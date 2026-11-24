"""Loop principal, modos foto/vídeo, menu por teclado e interação (Pessoa 2)."""

from __future__ import annotations

import sys
import time
import unicodedata
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np

from editor import CANAIS, FILTROS, OPERACOES, Passo, aplicar_pipeline

from .stickers import (
    carregar_stickers,
    colar_sticker,
    ler_imagem,
    redimensionar_sticker,
)

RAIZ = Path(__file__).resolve().parent.parent
PASTA_IMAGENS = RAIZ / "assets" / "imagens"
PASTA_STICKERS = RAIZ / "assets" / "stickers"
PASTA_SAIDAS = RAIZ / "saidas"

JANELA = "Editor de Imagens e Video"
TRACKBAR = "Param"
LADO_MAX = 1280  # fotos maiores são reduzidas ao abrir (mantém a edição fluida)
EXTENSOES_IMAGEM = {".png", ".jpg", ".jpeg", ".bmp", ".webp"}
FRACAO_STICKER = 0.25  # altura do sticker = 25% do menor lado da foto (escala 1.0)

TECLAS_CONFIRMAR = (13, 10, 32)  # Enter, Enter (Linux), espaço
TECLA_ESC = 27

# Catálogo único para o menu: primeiro os filtros, depois as operações.
EFEITOS = [("filtro", i, f) for i, f in enumerate(FILTROS)] + [
    ("operacao", i, o) for i, o in enumerate(OPERACOES)
]

AJUDA = """
=========================== TECLAS ===========================
  O        abrir foto (lista assets/imagens ou digite um caminho)
  V        ligar / desligar a webcam
  A / D    efeito anterior / próximo (mostra a descrição aqui)
  C        alternar canal: todos -> R -> G -> B
  Trackbar ajusta o parâmetro do efeito selecionado
  Enter    confirmar (aplica o efeito selecionado)
  Espaço   confirmar (igual ao Enter)
  P        liga / desliga a prévia do efeito selecionado
  B        carregar a imagem B (usada pelas operações)
  Z        desfazer o último efeito aplicado
  1-9      escolher sticker; clique na foto para colar (só modo foto)
  0        desativar sticker
  + / -    aumentar / diminuir o sticker
  U        remover o último sticker colado
  S        salvar o resultado em saidas/ (foto ou frame atual)
  R        resetar (volta à imagem original)
  H        mostrar esta ajuda
  Q / Esc  sair
==============================================================
"""


def _ascii(texto: str) -> str:
    """cv2.putText não desenha acentos: remove-os só no texto da tela."""
    return unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()


def limitar_lado(img: np.ndarray, lado_max: int = LADO_MAX) -> np.ndarray:
    maior = max(img.shape[:2])
    if maior <= lado_max:
        return img
    fator = lado_max / maior
    nova = (round(img.shape[1] * fator), round(img.shape[0] * fator))
    return cv2.resize(img, nova, interpolation=cv2.INTER_AREA)


def escolher_arquivo(pasta: Path, descricao: str) -> Path | None:
    """Pergunta no console: número da lista de `pasta` ou um caminho completo."""
    arquivos = []
    if pasta.exists():
        arquivos = sorted(p for p in pasta.iterdir() if p.suffix.lower() in EXTENSOES_IMAGEM)
    print(f"\n--- Escolher {descricao} ---")
    for i, arquivo in enumerate(arquivos, 1):
        print(f"  {i}) {arquivo.name}")
    entrada = input("Número da lista ou caminho completo (Enter cancela): ").strip().strip("\"'")
    if not entrada:
        return None
    if entrada.isdigit() and 1 <= int(entrada) <= len(arquivos):
        return arquivos[int(entrada) - 1]
    caminho = Path(entrada).expanduser()
    if caminho.is_file():
        return caminho
    print("Arquivo não encontrado.")
    return None


class Aplicacao:
    def __init__(self):
        self.foto: np.ndarray | None = None
        self.captura: cv2.VideoCapture | None = None
        self.frame: np.ndarray | None = None
        self.imagem_b: np.ndarray | None = None

        self.passos: list[Passo] = []  # histórico de edição (entrada do pipeline)
        self.efeito_atual = 0
        self.canal_atual = 0
        self.param = EFEITOS[0][2].param_padrao
        self.em_selecao = False  # True entre selecionar (A/D) e confirmar (Enter)
        self.previa = True

        self.stickers = carregar_stickers(PASTA_STICKERS)
        self.sticker_sel: int | None = None
        self.escala_sticker = 1.0
        self.colados: list[tuple[np.ndarray, int, int]] = []  # (bgra, x, y) já redimensionados

        self.resultado: np.ndarray | None = None  # o que é salvo (sem o texto da tela)
        self.sujo = True
        self.janela_pronta = False
        self._sincronizando = False
        self._mensagem = ""
        self._mensagem_ate = 0.0

    # ------------------------------------------------------------------
    # Estado
    # ------------------------------------------------------------------

    @property
    def modo(self) -> str:
        if self.captura is not None:
            return "video"
        return "foto" if self.foto is not None else "vazio"

    def original(self) -> np.ndarray | None:
        return self.frame if self.modo == "video" else self.foto

    def avisar(self, texto: str) -> None:
        print(texto)
        self._mensagem = texto
        self._mensagem_ate = time.time() + 3.0

    def efeito(self):
        return EFEITOS[self.efeito_atual]  # (tipo, indice, Filtro/Operacao)

    # ------------------------------------------------------------------
    # Pipeline
    # ------------------------------------------------------------------

    def montar_passo(self) -> Passo:
        tipo, indice, efeito = self.efeito()
        return Passo(
            tipo,
            indice,
            CANAIS[self.canal_atual],
            self.param if efeito.tem_param else None,
            self.imagem_b if tipo == "operacao" else None,
        )

    def calcular_resultado(self) -> np.ndarray:
        original = self.original()
        if original is None:
            return self._tela_vazia()

        passos = list(self.passos)
        if self.previa and self.em_selecao:
            candidato = self.montar_passo()
            if candidato.tipo == "filtro" or candidato.imagem_b is not None:
                passos.append(candidato)

        try:
            img = aplicar_pipeline(original, passos)
        except Exception as erro:  # não derruba a janela no meio de uma demonstração
            self.avisar(f"Erro ao aplicar efeito: {erro}")
            img = original.copy()

        if self.modo == "foto":
            for sticker, x, y in self.colados:
                img = colar_sticker(img, sticker, x, y)
        return img

    @staticmethod
    def _tela_vazia() -> np.ndarray:
        tela = np.zeros((480, 640, 3), np.uint8)
        cv2.putText(tela, "O = abrir foto   V = webcam   H = ajuda", (60, 240),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2, cv2.LINE_AA)
        return tela

    # ------------------------------------------------------------------
    # Menu: efeito, canal, confirmar, resetar
    # ------------------------------------------------------------------

    def selecionar_efeito(self, delta: int) -> None:
        self.efeito_atual = (self.efeito_atual + delta) % len(EFEITOS)
        self.em_selecao = True
        tipo, _, efeito = self.efeito()
        self.param = efeito.param_padrao
        self._sincronizar_trackbar()
        rotulo = "Filtro" if tipo == "filtro" else "Operação (precisa da imagem B)"
        print(f"\n{rotulo} {self.efeito_atual + 1}/{len(EFEITOS)}")
        print(efeito.ajuda())
        self.sujo = True

    def alternar_canal(self) -> None:
        self.canal_atual = (self.canal_atual + 1) % len(CANAIS)
        print(f"Canal: {CANAIS[self.canal_atual]}")
        self.sujo = True

    def confirmar(self) -> None:
        if self.modo == "vazio":
            self.avisar("Abra uma foto (O) ou ligue a webcam (V) primeiro.")
            return
        if not self.em_selecao:
            self.avisar("Escolha um efeito com A / D antes de confirmar.")
            return
        tipo, _, efeito = self.efeito()
        if tipo == "operacao" and self.imagem_b is None:
            self.carregar_imagem_b()
            if self.imagem_b is None:
                return
        self.passos.append(self.montar_passo())
        self.em_selecao = False
        self.sujo = True
        self.avisar(f"Aplicado: {efeito.nome} (canal {CANAIS[self.canal_atual]}). "
                    f"Passos: {len(self.passos)}")

    def desfazer(self) -> None:
        if self.passos:
            self.passos.pop()
            self.sujo = True
            self.avisar(f"Último efeito desfeito. Passos: {len(self.passos)}")

    def resetar(self) -> None:
        self.passos.clear()
        self.colados.clear()
        self.em_selecao = False
        self.sujo = True
        self.avisar("Resetado: imagem original.")

    # ------------------------------------------------------------------
    # Trackbar
    # ------------------------------------------------------------------

    def _ao_mover_trackbar(self, valor: int) -> None:
        if self._sincronizando:
            return
        efeito = self.efeito()[2]
        if efeito.tem_param:
            self.param = max(efeito.param_min, min(efeito.param_max, valor))
            self.sujo = True

    def _sincronizar_trackbar(self) -> None:
        """Ajusta faixa e posição da trackbar ao efeito selecionado."""
        if not self.janela_pronta:
            return
        efeito = self.efeito()[2]
        minimo, maximo = (efeito.param_min, efeito.param_max) if efeito.tem_param else (0, 1)
        posicao = efeito.param_padrao if efeito.tem_param else 0
        self._sincronizando = True
        try:
            try:
                cv2.setTrackbarMin(TRACKBAR, JANELA, 0)  # evita min > max no meio da troca
                cv2.setTrackbarMax(TRACKBAR, JANELA, maximo)
                cv2.setTrackbarMin(TRACKBAR, JANELA, minimo)
            except cv2.error:
                pass  # backend sem suporte: o pipeline já limita o valor à faixa do efeito
            cv2.setTrackbarPos(TRACKBAR, JANELA, posicao)
        finally:
            self._sincronizando = False

    # ------------------------------------------------------------------
    # Fotos e webcam
    # ------------------------------------------------------------------

    def definir_foto(self, img: np.ndarray) -> None:
        self.parar_webcam()
        self.foto = limitar_lado(img)
        self.passos.clear()
        self.colados.clear()
        self.em_selecao = False
        self.sujo = True

    def abrir_foto(self, caminho: Path | None = None) -> None:
        caminho = caminho or escolher_arquivo(PASTA_IMAGENS, "foto")
        if caminho is None:
            return
        img = ler_imagem(caminho)
        if img is None:
            self.avisar(f"Não foi possível abrir {Path(caminho).name}.")
            return
        self.definir_foto(img)
        self.avisar(f"Foto aberta: {Path(caminho).name} ({img.shape[1]}x{img.shape[0]})")

    def carregar_imagem_b(self) -> None:
        caminho = escolher_arquivo(PASTA_IMAGENS, "imagem B (para operações)")
        if caminho is None:
            return
        img = ler_imagem(caminho)
        if img is None:
            self.avisar(f"Não foi possível abrir {caminho.name}.")
            return
        self.imagem_b = img
        self.sujo = True
        self.avisar(f"Imagem B: {caminho.name}")

    def alternar_webcam(self) -> None:
        if self.captura is not None:
            self.parar_webcam()
            self.avisar("Webcam desligada.")
            return
        api = cv2.CAP_DSHOW if sys.platform.startswith("win") else cv2.CAP_ANY
        captura = cv2.VideoCapture(0, api)
        if not captura.isOpened():
            captura.release()
            self.avisar("Não foi possível abrir a webcam.")
            return
        self.captura = captura
        self.sticker_sel = None  # stickers só existem no modo foto
        self.avisar("Webcam ligada (V desliga).")

    def parar_webcam(self) -> None:
        if self.captura is not None:
            self.captura.release()
        self.captura = None
        self.frame = None
        self.sujo = True

    def _ler_frame(self) -> None:
        if self.captura is None:
            return
        ok, frame = self.captura.read()
        if ok:
            self.frame = cv2.flip(frame, 1)  # espelhado, como câmera frontal
        elif self.frame is None:
            self.avisar("A webcam não entregou imagem.")

    # ------------------------------------------------------------------
    # Stickers
    # ------------------------------------------------------------------

    def selecionar_sticker(self, indice: int | None) -> None:
        if indice is None:
            self.sticker_sel = None
            self.avisar("Sticker desativado.")
            return
        if self.modo != "foto":
            self.avisar("Stickers só funcionam no modo foto (abra uma foto com O).")
            return
        if indice >= len(self.stickers):
            self.avisar(f"Só há {len(self.stickers)} stickers em assets/stickers.")
            return
        self.sticker_sel = indice
        self.avisar(f"Sticker: {self.stickers[indice][0]}. Clique na foto para colar.")

    def ajustar_escala_sticker(self, passo: float) -> None:
        self.escala_sticker = round(min(3.0, max(0.2, self.escala_sticker + passo)), 2)
        self.avisar(f"Tamanho do sticker: x{self.escala_sticker:.1f}")

    def colar_em(self, x: int, y: int) -> None:
        """Cola o sticker selecionado centralizado em (x, y)."""
        if self.sticker_sel is None or self.foto is None:
            return
        altura_foto, largura_foto = self.foto.shape[:2]
        alvo = min(altura_foto, largura_foto) * FRACAO_STICKER * self.escala_sticker
        sticker = redimensionar_sticker(self.stickers[self.sticker_sel][1], alvo)
        h, w = sticker.shape[:2]
        self.colados.append((sticker, x - w // 2, y - h // 2))
        self.sujo = True

    def remover_ultimo_sticker(self) -> None:
        if self.colados:
            self.colados.pop()
            self.sujo = True

    def _ao_clicar(self, evento, x, y, _flags, _param) -> None:
        if evento == cv2.EVENT_LBUTTONDOWN and self.sticker_sel is not None and self.modo == "foto":
            self.colar_em(x, y)

    # ------------------------------------------------------------------
    # Salvar
    # ------------------------------------------------------------------

    def salvar(self) -> Path | None:
        if self.modo == "vazio" or self.resultado is None:
            self.avisar("Nada para salvar.")
            return None
        agora = datetime.now()
        prefixo = "frame" if self.modo == "video" else "resultado"
        nome = agora.strftime(f"{prefixo}_%Y%m%d_%H%M%S") + f"_{agora.microsecond // 1000:03d}.png"
        PASTA_SAIDAS.mkdir(exist_ok=True)
        caminho = PASTA_SAIDAS / nome
        if not cv2.imwrite(str(caminho), self.resultado):
            # imwrite falha em caminhos com acento no Windows; imencode contorna.
            ok, buffer = cv2.imencode(".png", self.resultado)
            if not ok:
                self.avisar("Erro ao salvar a imagem.")
                return None
            buffer.tofile(str(caminho))
        self.avisar(f"Salvo: saidas/{nome}")
        return caminho

    # ------------------------------------------------------------------
    # Teclado
    # ------------------------------------------------------------------

    def tratar_tecla(self, tecla: int) -> bool:
        """Processa uma tecla. Devolve False quando o usuário pede para sair."""
        if tecla == 255:  # waitKey sem tecla
            return True
        if 65 <= tecla <= 90:  # maiúsculas valem como minúsculas
            tecla += 32

        if tecla in (TECLA_ESC, ord("q")):
            return False
        if tecla in TECLAS_CONFIRMAR:
            self.confirmar()
        elif tecla == ord("o"):
            self.abrir_foto()
        elif tecla == ord("v"):
            self.alternar_webcam()
        elif tecla == ord("d"):
            self.selecionar_efeito(+1)
        elif tecla == ord("a"):
            self.selecionar_efeito(-1)
        elif tecla == ord("c"):
            self.alternar_canal()
        elif tecla == ord("p"):
            self.previa = not self.previa
            self.sujo = True
            self.avisar(f"Prévia {'ligada' if self.previa else 'desligada'}.")
        elif tecla == ord("b"):
            self.carregar_imagem_b()
        elif tecla == ord("z"):
            self.desfazer()
        elif tecla == ord("0"):
            self.selecionar_sticker(None)
        elif ord("1") <= tecla <= ord("9"):
            self.selecionar_sticker(tecla - ord("1"))
        elif tecla in (ord("+"), ord("=")):
            self.ajustar_escala_sticker(+0.1)
        elif tecla in (ord("-"), ord("_")):
            self.ajustar_escala_sticker(-0.1)
        elif tecla == ord("u"):
            self.remover_ultimo_sticker()
        elif tecla == ord("s"):
            self.salvar()
        elif tecla == ord("r"):
            self.resetar()
        elif tecla == ord("h"):
            print(AJUDA)
        return True

    # ------------------------------------------------------------------
    # Tela
    # ------------------------------------------------------------------

    def _linhas_hud(self) -> list[str]:
        rotulo_modo = {"foto": "FOTO", "video": "VIDEO", "vazio": "SEM IMAGEM"}[self.modo]
        linhas = [f"{rotulo_modo} | passos: {len(self.passos)} | stickers: {len(self.colados)}"]

        canal = CANAIS[self.canal_atual]
        if self.em_selecao:
            _, _, efeito = self.efeito()
            linha = f"Efeito {self.efeito_atual + 1}/{len(EFEITOS)}: {efeito.nome} | canal: {canal}"
            if efeito.tem_param:
                linha += f" | {efeito.param_nome}: {self.param}"
            linhas.append(linha + " | Enter aplica")
        else:
            linhas.append(f"Efeito: nenhum (A/D escolhe) | canal: {canal}")

        if self.sticker_sel is not None:
            nome = self.stickers[self.sticker_sel][0]
            linhas.append(f"Sticker: {nome} x{self.escala_sticker:.1f} (clique para colar)")
        else:
            linhas.append("H = ajuda de teclas")
        if time.time() < self._mensagem_ate:
            linhas.append(self._mensagem)
        return [_ascii(linha) for linha in linhas]

    def desenhar_hud(self, img: np.ndarray) -> np.ndarray:
        """Texto de status por cima de uma cópia: o resultado salvo fica limpo."""
        tela = img.copy()
        linhas = self._linhas_hud()
        altura_faixa = 22 * len(linhas) + 8
        faixa = tela[:altura_faixa]
        tela[:altura_faixa] = (faixa * 0.35).astype(np.uint8)  # escurece o fundo do texto
        for i, linha in enumerate(linhas):
            cv2.putText(tela, linha, (8, 22 + 22 * i), cv2.FONT_HERSHEY_SIMPLEX,
                        0.5, (255, 255, 255), 1, cv2.LINE_AA)
        return tela

    def _criar_janela(self) -> None:
        cv2.namedWindow(JANELA, cv2.WINDOW_AUTOSIZE)
        cv2.createTrackbar(TRACKBAR, JANELA, 0, 255, self._ao_mover_trackbar)
        cv2.setMouseCallback(JANELA, self._ao_clicar)
        self.janela_pronta = True
        self._sincronizar_trackbar()

    def executar(self, foto_inicial=None) -> None:
        self._criar_janela()
        print(AJUDA)
        if foto_inicial:
            self.abrir_foto(Path(foto_inicial))
        try:
            while True:
                self._ler_frame()
                if self.sujo or self.modo == "video":
                    self.resultado = self.calcular_resultado()
                    self.sujo = False
                cv2.imshow(JANELA, self.desenhar_hud(self.resultado))

                tecla = cv2.waitKey(1 if self.modo == "video" else 30) & 0xFF
                if not self.tratar_tecla(tecla):
                    break
                if cv2.getWindowProperty(JANELA, cv2.WND_PROP_VISIBLE) < 1:
                    break  # janela fechada no X
        finally:
            self.parar_webcam()
            cv2.destroyAllWindows()