"""Gera os stickers básicos em assets/stickers/ (PNG com canal alfa).

    python tools/gerar_stickers.py

Cada sticker é desenhado em alta resolução (1024 px) e reduzido para 256 px.
A redução suaviza as bordas e o canal alfa fica com transições suaves.
"""

from pathlib import Path

import cv2
import numpy as np

S = 1024  # resolução de desenho
TAMANHO = 256  # resolução final
CONTORNO = 24  # espessura do contorno preto em S
SAIDA = Path(__file__).resolve().parent.parent / "assets" / "stickers"

PRETO = (0, 0, 0)


def _salvar(nome, mascara, cor, detalhes=None):
    """Pinta a máscara com `cor`, aplica contorno preto e salva com alfa.

    `detalhes(bgr)` pode desenhar marcas extras (ex.: faixa da cartola).
    """
    bgr = np.full((S, S, 3), cor, np.uint8)
    if detalhes is not None:
        detalhes(bgr)

    interior = cv2.erode(mascara, np.ones((CONTORNO, CONTORNO), np.uint8))
    contorno = (mascara > 0) & (interior == 0)
    bgr[contorno] = PRETO

    rgba = cv2.merge([*cv2.split(bgr), mascara])
    rgba = cv2.resize(rgba, (TAMANHO, TAMANHO), interpolation=cv2.INTER_AREA)
    cv2.imwrite(str(SAIDA / f"{nome}.png"), rgba)
    print(f"Gerado: {SAIDA / (nome + '.png')}")


def _vazio():
    return np.zeros((S, S), np.uint8)


# --------------------------------------------------------------------------


def cartola():
    m = _vazio()
    cv2.rectangle(m, (300, 170), (724, 640), 255, -1)  # copa
    cv2.ellipse(m, (512, 650), (330, 70), 0, 0, 360, 255, -1)  # aba

    def faixa(bgr):
        cv2.rectangle(bgr, (300, 540), (724, 640), (40, 40, 200), -1)  # faixa vermelha

    _salvar("cartola", m, (35, 35, 35), faixa)


def cachimbo():
    m = _vazio()
    # Fornilho: bojo cônico (boca larga em cima, base estreita embaixo)
    cv2.fillPoly(m, [np.array([[300, 420], [560, 420], [500, 640], [360, 640]], np.int32)], 255)
    cv2.ellipse(m, (430, 420), (130, 50), 0, 0, 360, 255, -1)  # borda da boca
    cv2.ellipse(m, (430, 640), (70, 24), 0, 0, 360, 255, -1)  # base arredondada
    # Haste saindo do lado do bojo, inclinada para cima
    cv2.line(m, (530, 480), (790, 300), 255, 70)
    cv2.circle(m, (530, 480), 35, 255, -1)
    # Piteira
    cv2.line(m, (770, 318), (850, 262), 255, 62)

    def detalhes(bgr):
        cv2.ellipse(bgr, (430, 420), (105, 32), 0, 0, 360, (25, 40, 65), -1)  # abertura da boca
        cv2.line(bgr, (770, 318), (850, 262), (0, 0, 0), 62)  # piteira preta
        cv2.circle(bgr, (850, 262), 31, (0, 0, 0), -1)

    _salvar("cachimbo", m, (40, 70, 120), detalhes)


def balao_fala():
    m = _vazio()
    cv2.ellipse(m, (512, 420), (380, 270), 0, 0, 360, 255, -1)
    cv2.fillPoly(m, [np.array([[300, 600], [250, 880], [560, 640]], np.int32)], 255)
    _salvar("balao_fala", m, (255, 255, 255))


def balao_pensamento():
    m = _vazio()
    cv2.ellipse(m, (512, 430), (330, 230), 0, 0, 360, 255, -1)
    # "Nuvem": círculos ao redor do centro
    for ang in range(0, 360, 40):
        x = int(512 + 330 * np.cos(np.radians(ang)))
        y = int(430 + 230 * np.sin(np.radians(ang)))
        cv2.circle(m, (x, y), 115, 255, -1)
    # Bolhinhas que levam ao personagem
    cv2.circle(m, (330, 720), 60, 255, -1)
    cv2.circle(m, (255, 835), 36, 255, -1)
    _salvar("balao_pensamento", m, (255, 255, 255))


def estrela():
    cx, cy, r_ext, r_int = 512, 540, 430, 180
    pontos = []
    for i in range(10):
        r = r_ext if i % 2 == 0 else r_int
        ang = np.radians(-90 + i * 36)
        pontos.append([int(cx + r * np.cos(ang)), int(cy + r * np.sin(ang))])
    m = _vazio()
    cv2.fillPoly(m, [np.array(pontos, np.int32)], 255)
    _salvar("estrela", m, (0, 215, 255))  # dourado em BGR


if __name__ == "__main__":
    SAIDA.mkdir(parents=True, exist_ok=True)
    cartola()
    cachimbo()
    balao_fala()
    balao_pensamento()
    estrela()
