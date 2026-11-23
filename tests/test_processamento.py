import numpy as np
import pytest

from editor import CANAIS, FILTROS, OPERACOES, Passo, aplicar_pipeline

rng = np.random.default_rng(0)
IMG = rng.integers(0, 256, (60, 80, 3), dtype=np.uint8)
IMG_B = rng.integers(0, 256, (45, 100, 3), dtype=np.uint8)  # tamanho diferente de propósito


def _valores_de_param(efeito):
    if not efeito.tem_param:
        return [None]
    return [efeito.param_min, efeito.param_padrao, efeito.param_max]


@pytest.mark.parametrize("canal", CANAIS)
@pytest.mark.parametrize("indice", range(len(FILTROS)))
def test_filtros_devolvem_bgr_do_mesmo_tamanho(indice, canal):
    for param in _valores_de_param(FILTROS[indice]):
        saida = aplicar_pipeline(IMG, [Passo("filtro", indice, canal, param)])
        assert saida.shape == IMG.shape
        assert saida.dtype == np.uint8


@pytest.mark.parametrize("canal", CANAIS)
@pytest.mark.parametrize("indice", range(len(OPERACOES)))
def test_operacoes_redimensionam_a_segunda_imagem(indice, canal):
    for param in _valores_de_param(OPERACOES[indice]):
        saida = aplicar_pipeline(IMG, [Passo("operacao", indice, canal, param, IMG_B)])
        assert saida.shape == IMG.shape
        assert saida.dtype == np.uint8


def test_requisitos_minimos():
    assert len(FILTROS) >= 10
    assert len(OPERACOES) >= 3
    for efeito in FILTROS + OPERACOES:
        assert efeito.descricao
        assert efeito.nome in efeito.ajuda()


def _indice(nome, lista=FILTROS):
    return next(i for i, f in enumerate(lista) if f.nome == nome)


def test_canal_unico_mostra_o_canal_em_cinza():
    # Negativo só no R: as três camadas da saída devem ser 255 - R.
    saida = aplicar_pipeline(IMG, [Passo("filtro", _indice("Negativo"), "R")])
    esperado = 255 - IMG[:, :, 2]
    for c in range(3):
        assert np.array_equal(saida[:, :, c], esperado)


def test_combinacao_de_filtros():
    neg = _indice("Negativo")
    saida = aplicar_pipeline(IMG, [Passo("filtro", neg), Passo("filtro", neg)])
    assert np.array_equal(saida, IMG)


def test_suavizacao_preserva_imagem_constante():
    constante = np.full((30, 30, 3), 90, np.uint8)
    for nome in ("Box blur", "Gaussian blur", "Mediana"):
        saida = aplicar_pipeline(constante, [Passo("filtro", _indice(nome), param=9)])
        assert np.array_equal(saida, constante)


def test_blending_nos_extremos():
    blend = _indice("Blending", OPERACOES)
    so_a = aplicar_pipeline(IMG, [Passo("operacao", blend, param=100, imagem_b=IMG)])
    assert np.array_equal(so_a, IMG)


def test_soma_satura_em_255():
    a = np.full((4, 4, 3), 200, np.uint8)
    b = np.full((4, 4, 3), 100, np.uint8)
    saida = aplicar_pipeline(a, [Passo("operacao", _indice("Adição", OPERACOES), imagem_b=b)])
    assert (saida == 255).all()


def test_pipeline_nao_altera_a_original():
    copia = IMG.copy()
    saida = aplicar_pipeline(IMG, [])
    saida[:] = 0
    assert np.array_equal(IMG, copia)


def test_param_fora_do_intervalo_e_limitado():
    brilho = _indice("Brilho")
    assert np.array_equal(
        aplicar_pipeline(IMG, [Passo("filtro", brilho, param=9999)]),
        aplicar_pipeline(IMG, [Passo("filtro", brilho, param=FILTROS[brilho].param_max)]),
    )


def test_operacao_sem_segunda_imagem_da_erro():
    with pytest.raises(ValueError):
        aplicar_pipeline(IMG, [Passo("operacao", 0)])
