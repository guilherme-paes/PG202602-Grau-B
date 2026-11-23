"""Operações aritméticas entre duas imagens (Pessoa 1).

Assinatura: (a, b, param) -> imagem. O pipeline garante que `b` já chega com
o mesmo tamanho e o mesmo número de canais de `a`. As contas são feitas em
float32 e saturadas em [0, 255] no final, para não haver overflow do uint8
(em uint8, 200 + 100 daria 44).
"""

import numpy as np

from .contrato import Operacao
from .filtros import _saturar


def soma(a, b, _param):
    return _saturar(a.astype(np.float32) + b)


def subtracao_ponderada(a, b, peso):
    w = peso / 100
    return _saturar(a.astype(np.float32) - w * b)


def blending(a, b, alfa):
    t = alfa / 100
    return _saturar(t * a.astype(np.float32) + (1 - t) * b)


def diferenca_absoluta(a, b, _param):
    return _saturar(np.abs(a.astype(np.float32) - b))


OPERACOES = [
    Operacao(
        "Adição",
        "Soma pixel a pixel: S = A + B, saturando em 255. Clareia e sobrepõe as duas imagens.",
        soma,
    ),
    Operacao(
        "Subtração ponderada",
        "S = A - w·B, saturando em 0. Remove de A o conteúdo de B na proporção w (peso/100).",
        subtracao_ponderada,
        "peso de B (%)", 0, 100, 50,
    ),
    Operacao(
        "Blending",
        "Mistura linear: S = α·A + (1 - α)·B, com α = alfa/100. "
        "Com 100 só aparece A; com 0 só aparece B.",
        blending,
        "alfa (%)", 0, 100, 50,
    ),
    Operacao(
        "Diferença absoluta",
        "S = |A - B|. Pixels iguais ficam pretos; destaca onde as imagens diferem.",
        diferenca_absoluta,
    ),
]
