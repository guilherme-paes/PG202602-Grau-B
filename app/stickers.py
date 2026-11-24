
from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np


def ler_imagem(caminho, flags=cv2.IMREAD_COLOR):
    """Lê uma imagem do disco. Devolve None se o arquivo não puder ser lido.

    Usa np.fromfile + imdecode porque cv2.imread falha no Windows quando o
    caminho tem acentos (ex.: "São Leopoldo").
    """
    try:
        dados = np.fromfile(str(caminho), dtype=np.uint8)
    except OSError:
        return None
    if dados.size == 0:
        return None
    return cv2.imdecode(dados, flags)


def para_bgra(img: np.ndarray) -> np.ndarray:
    """Normaliza cinza, BGR ou BGRA (uint8 ou uint16) para BGRA uint8."""
    if img.dtype != np.uint8:
        img = (img.astype(np.float32) / 257).astype(np.uint8)
    if img.ndim == 2:
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    if img.shape[2] == 3:
        opaco = np.full(img.shape[:2] + (1,), 255, np.uint8)
        img = np.concatenate([img, opaco], axis=2)
    return img


def carregar_stickers(pasta) -> list[tuple[str, np.ndarray]]:
    """Carrega todos os PNGs da pasta, em ordem alfabética: [(nome, bgra), ...]."""
    stickers = []
    for arquivo in sorted(Path(pasta).glob("*.png")):
        img = ler_imagem(arquivo, cv2.IMREAD_UNCHANGED)
        if img is None:
            print(f"Aviso: não foi possível ler o sticker {arquivo.name}")
            continue
        stickers.append((arquivo.stem, para_bgra(img)))
    return stickers


def redimensionar_sticker(sticker_bgra: np.ndarray, altura: float) -> np.ndarray:
    """Muda a altura do sticker mantendo a proporção.

    A interpolação é feita com as cores pré-multiplicadas pelo alfa. Sem isso,
    os pixels transparentes (geralmente pretos) "sujariam" a borda do sticker
    com um halo escuro.
    """
    h, w = sticker_bgra.shape[:2]
    nova_altura = max(1, int(round(altura)))
    nova_largura = max(1, int(round(w * nova_altura / h)))
    interp = cv2.INTER_AREA if nova_altura < h else cv2.INTER_LINEAR

    alfa = sticker_bgra[:, :, 3:4].astype(np.float32) / 255
    premultiplicado = np.concatenate(
        [sticker_bgra[:, :, :3].astype(np.float32) * alfa, alfa], axis=2
    )
    premultiplicado = cv2.resize(
        premultiplicado, (nova_largura, nova_altura), interpolation=interp
    )

    novo_alfa = premultiplicado[:, :, 3:4]
    cores = premultiplicado[:, :, :3] / np.maximum(novo_alfa, 1e-6)
    saida = np.concatenate([cores, novo_alfa * 255], axis=2)
    return np.clip(np.rint(saida), 0, 255).astype(np.uint8)


def colar_sticker(imagem: np.ndarray, sticker_bgra: np.ndarray, x: int, y: int) -> np.ndarray:
    """Cola o sticker na imagem com (x, y) = canto superior esquerdo do sticker.

    Composição alfa feita à mão, pixel a pixel:
        saída = α · sticker + (1 − α) · fundo,   com α = A / 255

    x e y podem ser negativos, e o sticker pode passar das bordas: só o trecho
    que cai dentro da imagem é composto. Devolve uma imagem nova (a de entrada
    não é modificada).
    """
    saida = imagem.copy()
    if saida.ndim == 2:
        saida = cv2.cvtColor(saida, cv2.COLOR_GRAY2BGR)

    altura, largura = saida.shape[:2]
    h, w = sticker_bgra.shape[:2]
    x, y = int(x), int(y)

    # Interseção entre o retângulo do sticker e o da imagem (coords da imagem).
    x0, y0 = max(x, 0), max(y, 0)
    x1, y1 = min(x + w, largura), min(y + h, altura)
    if x0 >= x1 or y0 >= y1:
        return saida  # sticker totalmente fora

    # Mesmo trecho em coordenadas do sticker.
    recorte = sticker_bgra[y0 - y : y1 - y, x0 - x : x1 - x]
    alfa = recorte[:, :, 3:4].astype(np.float32) / 255
    cores = recorte[:, :, :3].astype(np.float32)
    fundo = saida[y0:y1, x0:x1].astype(np.float32)

    mistura = alfa * cores + (1 - alfa) * fundo
    saida[y0:y1, x0:x1] = np.clip(np.rint(mistura), 0, 255).astype(np.uint8)
    return saida