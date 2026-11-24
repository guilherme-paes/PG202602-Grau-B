
import numpy as np

from app.aplicacao import EFEITOS, Aplicacao


def _foto(h=120, w=160):
    rng = np.random.default_rng(0)
    return rng.integers(0, 256, (h, w, 3), dtype=np.uint8)


def _app():
    app = Aplicacao()
    app.definir_foto(_foto())
    return app


def test_confirmar_sem_selecionar_nao_cria_passo():
    app = _app()
    app.confirmar()
    assert app.passos == []


def test_selecionar_e_confirmar_filtro_adiciona_passo():
    app = _app()
    app.selecionar_efeito(+1)  # Negativo
    app.confirmar()
    assert len(app.passos) == 1
    assert app.passos[0].tipo == "filtro" and app.passos[0].indice == 1
    assert not app.em_selecao


def test_previa_nao_muda_historico_mas_muda_imagem():
    app = _app()
    original = app.calcular_resultado()
    app.selecionar_efeito(+1)  # Negativo
    previa = app.calcular_resultado()
    assert app.passos == []
    assert (previa == 255 - original).all()


def test_param_vai_para_o_passo():
    app = _app()
    app.selecionar_efeito(+4)  # Box blur
    app.param = 9
    app.confirmar()
    assert app.passos[0].param == 9


def test_filtros_encadeados():
    app = _app()
    for _ in range(2):
        app.selecionar_efeito(+1)
        app.confirmar()
    assert len(app.passos) == 2


def test_canal_unico_mostra_so_aquele_canal():
    app = _app()
    app.alternar_canal()  # R
    app.selecionar_efeito(+1)  # Negativo
    app.confirmar()
    saida = app.calcular_resultado()
    assert (saida[:, :, 0] == saida[:, :, 1]).all() and (saida[:, :, 1] == saida[:, :, 2]).all()
    assert (saida[:, :, 0] == 255 - app.foto[:, :, 2]).all()  # canal R do OpenCV = índice 2


def test_operacao_exige_imagem_b():
    app = _app()
    app.selecionar_efeito(-1)  # última operação
    assert EFEITOS[app.efeito_atual][0] == "operacao"
    app.calcular_resultado()  # prévia sem B não pode quebrar
    app.imagem_b = _foto(50, 50)  # tamanho diferente: o pipeline redimensiona
    app.confirmar()
    assert len(app.passos) == 1
    assert app.calcular_resultado().shape == app.foto.shape


def test_resetar_limpa_passos_e_stickers():
    app = _app()
    app.selecionar_efeito(+1)
    app.confirmar()
    app.selecionar_sticker(0)
    app.colar_em(50, 50)
    assert app.passos and app.colados
    app.resetar()
    assert app.passos == [] and app.colados == []
    assert (app.calcular_resultado() == app.foto).all()


def test_sticker_aparece_no_resultado_e_nao_sofre_filtro():
    app = _app()
    app.selecionar_efeito(+1)  # Negativo
    app.confirmar()
    app.selecionar_sticker(0)  # coração
    app.colar_em(80, 60)
    com = app.calcular_resultado()
    app.colados.clear()
    sem = app.calcular_resultado()
    assert not (com == sem).all()


def test_sticker_colado_na_borda_nao_quebra():
    app = _app()
    app.selecionar_sticker(2)
    for x, y in [(0, 0), (159, 119), (-50, 60), (400, 400)]:
        app.colar_em(x, y)
    assert app.calcular_resultado().shape == app.foto.shape


def test_stickers_so_no_modo_foto():
    app = Aplicacao()  # sem foto
    app.selecionar_sticker(0)
    assert app.sticker_sel is None


def test_foto_grande_e_reduzida():
    app = Aplicacao()
    app.definir_foto(np.zeros((3000, 4000, 3), np.uint8))
    assert max(app.foto.shape[:2]) == 1280


def test_salvar_escreve_arquivo(tmp_path, monkeypatch):
    import app.aplicacao as mod

    monkeypatch.setattr(mod, "PASTA_SAIDAS", tmp_path)
    app = _app()
    app.resultado = app.calcular_resultado()
    caminho = app.salvar()
    assert caminho is not None and caminho.exists() and caminho.name.startswith("resultado_")


def test_teclas_basicas():
    app = _app()
    assert app.tratar_tecla(ord("D")) is True  # maiúscula vale
    assert app.em_selecao
    assert app.tratar_tecla(13) is True
    assert len(app.passos) == 1
    assert app.tratar_tecla(ord("r")) is True and app.passos == []
    assert app.tratar_tecla(ord("q")) is False
    assert app.tratar_tecla(255) is True