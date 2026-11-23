"""Filtros de imagem (Pessoa 1).

Todo filtro tem a assinatura (imagem, param) -> imagem e precisa aceitar tanto
uma imagem BGR (3 canais) quanto um único canal (2D), porque o pipeline passa
só o canal escolhido quando o usuário seleciona R, G ou B. A saída pode ter 1 ou
3 canais: o pipeline converte tudo para BGR no final.

Os filtros de convolução (box, sharpen, Laplaciano e Sobel) montam o kernel à
mão e usam cv2.filter2D, para deixar a máscara visível no código.
"""

import cv2
import numpy as np

from .contrato import Filtro

# --------------------------------------------------------------------------
# Auxiliares
# --------------------------------------------------------------------------


def _cinza(img: np.ndarray) -> np.ndarray:
    return img if img.ndim == 2 else cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)


def _impar(k: int) -> int:
    """Tamanho de kernel válido: no mínimo 1 e sempre ímpar (tem centro)."""
    k = max(1, int(k))
    return k if k % 2 == 1 else k + 1


def _saturar(img: np.ndarray) -> np.ndarray:
    """Corta os valores em [0, 255] e volta para uint8."""
    return np.clip(img, 0, 255).astype(np.uint8)


# --------------------------------------------------------------------------
# Transformações de intensidade (ponto a ponto)
# --------------------------------------------------------------------------


def escala_de_cinza(img, _param):
    return _cinza(img)


def negativo(img, _param):
    return 255 - img  # s = (L - 1) - r, com L = 256


# Matriz de sépia em ordem BGR: cada linha gera um canal de saída (B', G', R')
# a partir de (B, G, R) de entrada.
_SEPIA = np.array(
    [
        [0.131, 0.534, 0.272],  # B'
        [0.168, 0.686, 0.349],  # G'
        [0.189, 0.769, 0.393],  # R'
    ],
    dtype=np.float32,
)


def sepia(img, intensidade):
    if img.ndim == 2:
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    tom = cv2.transform(img, _SEPIA)  # já satura em 255
    a = intensidade / 100
    return cv2.addWeighted(tom, a, img, 1 - a, 0)


def brilho(img, nivel):
    delta = nivel - 100  # 100 = sem alteração
    return _saturar(img.astype(np.int16) + delta)


# --------------------------------------------------------------------------
# Suavização (passa-baixa)
# --------------------------------------------------------------------------


def box_blur(img, tamanho):
    k = _impar(tamanho)
    kernel = np.ones((k, k), np.float32) / (k * k)  # média simples
    return cv2.filter2D(img, -1, kernel)


def gaussian_blur(img, tamanho):
    k = _impar(tamanho)
    return cv2.GaussianBlur(img, (k, k), 0)  # sigma = 0 -> calculado a partir de k


def mediana(img, tamanho):
    k = _impar(tamanho)
    if k < 3:
        return img.copy()  # cv2.medianBlur exige k >= 3
    return cv2.medianBlur(img, k)


# --------------------------------------------------------------------------
# Realce e bordas (passa-alta)
# --------------------------------------------------------------------------

_LAPLACIANO = np.array(
    [
        [0, 1, 0],
        [1, -4, 1],
        [0, 1, 0],
    ],
    dtype=np.float32,
)

_IDENTIDADE = np.array(
    [
        [0, 0, 0],
        [0, 1, 0],
        [0, 0, 0],
    ],
    dtype=np.float32,
)

_SOBEL_X = np.array(
    [
        [-1, 0, 1],
        [-2, 0, 2],
        [-1, 0, 1],
    ],
    dtype=np.float32,
)
_SOBEL_Y = _SOBEL_X.T


def sharpen(img, intensidade):
    # g = f - a * Laplaciano(f)  ->  kernel = identidade - a * Laplaciano.
    # Com a = 1 vira o clássico [[0,-1,0], [-1,5,-1], [0,-1,0]].
    a = intensidade / 10
    kernel = _IDENTIDADE - a * _LAPLACIANO
    return cv2.filter2D(img, -1, kernel)


def laplaciano(img, ganho):
    # Saída em float porque a resposta tem valores negativos; o módulo mostra
    # a intensidade da borda independente do sinal.
    resposta = cv2.filter2D(_cinza(img), cv2.CV_32F, _LAPLACIANO)
    return _saturar(np.abs(resposta) * ganho)


def sobel(img, direcao):
    cinza = _cinza(img)
    gx = cv2.filter2D(cinza, cv2.CV_32F, _SOBEL_X)
    gy = cv2.filter2D(cinza, cv2.CV_32F, _SOBEL_Y)
    if direcao == 0:
        resposta = np.abs(gx)
    elif direcao == 1:
        resposta = np.abs(gy)
    else:
        resposta = cv2.magnitude(gx, gy)  # sqrt(gx² + gy²)
    return _saturar(resposta)


def canny(img, limiar_inferior):
    suave = cv2.GaussianBlur(_cinza(img), (5, 5), 0)
    return cv2.Canny(suave, limiar_inferior, 2 * limiar_inferior)


def limiarizacao(img, limiar):
    _, binaria = cv2.threshold(_cinza(img), limiar, 255, cv2.THRESH_BINARY)
    return binaria


# --------------------------------------------------------------------------
# Catálogo (a ordem aqui é a ordem do menu)
# --------------------------------------------------------------------------

FILTROS = [
    Filtro(
        "Escala de cinza",
        "Converte para tons de cinza pela luminância: Y = 0.299R + 0.587G + 0.114B.",
        escala_de_cinza,
    ),
    Filtro(
        "Negativo",
        "Inverte as intensidades (s = 255 - r): claros viram escuros e cores viram complementares.",
        negativo,
    ),
    Filtro(
        "Sépia",
        "Tom envelhecido: cada canal de saída é uma combinação linear de R, G e B. "
        "A intensidade mistura o resultado com a imagem original.",
        sepia,
        "intensidade (%)", 0, 100, 100,
    ),
    Filtro(
        "Brilho",
        "Soma uma constante a todos os pixels, saturando em 0 e 255. "
        "100 mantém a imagem; abaixo escurece, acima clareia.",
        brilho,
        "nível", 0, 200, 140,
    ),
    Filtro(
        "Box blur",
        "Suavização pela média dos vizinhos: convolução com um kernel k×k de valores 1/k². "
        "Tamanhos pares são arredondados para o ímpar seguinte.",
        box_blur,
        "tamanho do kernel", 1, 31, 5,
    ),
    Filtro(
        "Gaussian blur",
        "Suavização com pesos gaussianos (vizinhos próximos pesam mais), "
        "mais natural que o box. O sigma é calculado a partir do tamanho do kernel.",
        gaussian_blur,
        "tamanho do kernel", 1, 31, 7,
    ),
    Filtro(
        "Mediana",
        "Troca cada pixel pela mediana da vizinhança k×k. Remove ruído "
        "sal-e-pimenta preservando bordas melhor que a média.",
        mediana,
        "tamanho do kernel", 1, 31, 5,
    ),
    Filtro(
        "Sharpen",
        "Realce de detalhes: subtrai da imagem o seu Laplaciano "
        "(kernel = identidade - a·Laplaciano, com a = intensidade/10).",
        sharpen,
        "intensidade", 0, 30, 10,
    ),
    Filtro(
        "Laplaciano",
        "Detector de bordas pela segunda derivada (kernel [[0,1,0],[1,-4,1],[0,1,0]]). "
        "Mostra o módulo da resposta; o ganho multiplica o resultado para destacar bordas fracas.",
        laplaciano,
        "ganho", 1, 10, 4,
    ),
    Filtro(
        "Sobel",
        "Bordas pela primeira derivada (gradiente) com os kernels de Sobel. "
        "Direção: 0 = horizontal (Gx), 1 = vertical (Gy), 2 = magnitude do gradiente.",
        sobel,
        "direção", 0, 2, 2,
    ),
    Filtro(
        "Canny",
        "Detector de bordas de Canny: suaviza (gaussiano 5×5), calcula o gradiente e liga as bordas "
        "por histerese. O limiar superior é o dobro do inferior.",
        canny,
        "limiar inferior", 0, 255, 60,
    ),
    Filtro(
        "Limiarização",
        "Binariza a imagem: pixels acima do limiar ficam brancos (255), os demais pretos (0).",
        limiarizacao,
        "limiar", 0, 255, 127,
    ),
]
