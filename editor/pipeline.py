"""Aplica a lista de passos sobre a imagem original (Pessoa 1).

O pipeline sempre recomeça da original. Isso dá a combinação de filtros (cada
passo recebe o resultado do anterior) e torna o "Resetar" trivial: basta
esvaziar a lista de passos.
"""

import cv2
import numpy as np

from .contrato import Passo
from .filtros import FILTROS
from .operacoes import OPERACOES

_INDICE_CANAL = {"B": 0, "G": 1, "R": 2}  # o OpenCV guarda os canais em BGR


def para_bgr(img: np.ndarray) -> np.ndarray:
    """Normaliza qualquer imagem (cinza, BGR ou BGRA) para BGR de 3 canais."""
    if img.ndim == 2:
        return cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    if img.shape[2] == 4:
        return cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
    return img


def selecionar_canal(img: np.ndarray, canal: str) -> np.ndarray:
    """Imagem inteira se canal == "todos"; senão só o canal R, G ou B (2D)."""
    if canal == "todos":
        return img
    if canal not in _INDICE_CANAL:
        raise ValueError(f"Canal inválido: {canal!r}")
    return cv2.extractChannel(img, _INDICE_CANAL[canal])


def _param_efetivo(efeito, param):
    if not efeito.tem_param:
        return 0
    if param is None:
        return efeito.param_padrao
    return min(max(int(param), efeito.param_min), efeito.param_max)


def _ajustar_ao_tamanho(b: np.ndarray, ref: np.ndarray) -> np.ndarray:
    altura, largura = ref.shape[:2]
    if b.shape[:2] == (altura, largura):
        return b
    encolhendo = b.shape[0] * b.shape[1] > altura * largura
    interp = cv2.INTER_AREA if encolhendo else cv2.INTER_LINEAR
    return cv2.resize(b, (largura, altura), interpolation=interp)


def aplicar_passo(img: np.ndarray, passo: Passo) -> np.ndarray:
    """Aplica um único passo. Entrada e saída em BGR."""
    entrada = selecionar_canal(img, passo.canal)

    if passo.tipo == "filtro":
        filtro = FILTROS[passo.indice]
        saida = filtro.aplicar(entrada, _param_efetivo(filtro, passo.param))

    elif passo.tipo == "operacao":
        if passo.imagem_b is None:
            raise ValueError("Operações precisam de uma segunda imagem (passo.imagem_b).")
        operacao = OPERACOES[passo.indice]
        b = _ajustar_ao_tamanho(para_bgr(passo.imagem_b), img)
        b = selecionar_canal(b, passo.canal)
        saida = operacao.aplicar(entrada, b, _param_efetivo(operacao, passo.param))

    else:
        raise ValueError(f"Tipo de passo inválido: {passo.tipo!r}")

    # Com um canal selecionado a saída é 2D: vira BGR cinza, então a tela mostra
    # exatamente o resultado daquele canal.
    return para_bgr(saida)


def aplicar_pipeline(original: np.ndarray, passos: list[Passo]) -> np.ndarray:
    """Aplica todos os passos em sequência e devolve uma imagem BGR nova.

    A original nunca é modificada, então a aplicação pode desenhar (stickers,
    textos) no resultado sem medo.
    """
    img = para_bgr(original).copy()
    for passo in passos:
        img = aplicar_passo(img, passo)
    return img
