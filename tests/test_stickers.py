
import numpy as np

from app.stickers import carregar_stickers, colar_sticker, redimensionar_sticker
from app.aplicacao import PASTA_STICKERS


def _fundo(valor=0, h=100, w=100):
    return np.full((h, w, 3), valor, np.uint8)


def _sticker(cor=(255, 255, 255), alfa=255, h=10, w=10):
    s = np.zeros((h, w, 4), np.uint8)
    s[:, :, :3] = cor
    s[:, :, 3] = alfa
    return s


def test_sticker_opaco_substitui_o_fundo():
    saida = colar_sticker(_fundo(0), _sticker((10, 20, 30)), 40, 40)
    assert (saida[40:50, 40:50] == (10, 20, 30)).all()
    assert saida[39, 39].tolist() == [0, 0, 0] and saida[50, 50].tolist() == [0, 0, 0]


def test_sticker_transparente_nao_altera():
    fundo = _fundo(77)
    assert (colar_sticker(fundo, _sticker(alfa=0), 10, 10) == fundo).all()


def test_alfa_parcial_mistura_linearmente():
    # saída = α·sticker + (1-α)·fundo, com α = 128/255
    saida = colar_sticker(_fundo(0), _sticker((255, 255, 255), alfa=128), 0, 0)
    assert abs(int(saida[5, 5, 0]) - 128) <= 1
    saida = colar_sticker(_fundo(200), _sticker((100, 100, 100), alfa=128), 0, 0)
    esperado = 128 / 255 * 100 + (1 - 128 / 255) * 200
    assert abs(int(saida[5, 5, 0]) - esperado) <= 1


def test_nao_modifica_a_imagem_de_entrada():
    fundo = _fundo(0)
    colar_sticker(fundo, _sticker(), 10, 10)
    assert fundo.max() == 0


def test_parcialmente_fora_em_todas_as_bordas():
    s = _sticker((9, 9, 9), h=10, w=10)
    for x, y in [(-4, 50), (95, 50), (50, -4), (50, 95), (-4, -4), (95, 95)]:
        saida = colar_sticker(_fundo(0), s, x, y)
        # só a parte que cai dentro da imagem é pintada
        esperado = np.zeros((100, 100), bool)
        esperado[max(y, 0): min(y + 10, 100), max(x, 0): min(x + 10, 100)] = True
        assert ((saida[:, :, 0] == 9) == esperado).all(), (x, y)


def test_totalmente_fora_nao_altera_nem_da_erro():
    fundo = _fundo(5)
    for x, y in [(-10, 0), (100, 0), (0, -10), (0, 100), (-500, -500), (500, 500)]:
        assert (colar_sticker(fundo, _sticker(), x, y) == fundo).all()


def test_sticker_maior_que_a_imagem():
    saida = colar_sticker(_fundo(0, 20, 20), _sticker((7, 7, 7), h=50, w=50), -10, -10)
    assert (saida == 7).all()


def test_funciona_com_imagem_cinza():
    cinza = np.zeros((30, 30), np.uint8)
    assert colar_sticker(cinza, _sticker(), 5, 5).shape == (30, 30, 3)


def test_redimensionar_mantem_proporcao_e_nao_cria_halo():
    s = np.zeros((100, 200, 4), np.uint8)  # transparente com pixels pretos
    s[30:70, 60:140] = (0, 0, 255, 255)  # retângulo vermelho opaco
    pequeno = redimensionar_sticker(s, 50)
    assert pequeno.shape == (50, 100, 4)
    visiveis = pequeno[pequeno[:, :, 3] > 0]
    # sem halo: toda cor visível continua vermelha pura (B e G ~ 0, R ~ 255)
    assert visiveis[:, 2].min() >= 250 and visiveis[:, :2].max() <= 3


def test_stickers_do_projeto_tem_alfa():
    stickers = carregar_stickers(PASTA_STICKERS)
    assert len(stickers) >= 5
    for nome, bgra in stickers:
        assert bgra.ndim == 3 and bgra.shape[2] == 4 and bgra.dtype == np.uint8, nome
        assert bgra[:, :, 3].min() == 0 and bgra[:, :, 3].max() == 255, nome  # tem transparência