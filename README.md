# PG202602-Grau-B

Protótipo de um editor de imagens e vídeo inspirado nos *stories* do Instagram, desenvolvido para o Grau B de Processamento Gráfico (Unisinos). O usuário carrega uma foto (**Modo Foto**) ou abre a webcam (**Modo Vídeo**) e aplica filtros, operações entre duas imagens e *stickers*.

Feito em Python com OpenCV.

## Integrantes

- Gabriel Gomes
- Guilherme Paes

## Instalação

Requer Python 3.10 ou mais recente.

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux / macOS
source .venv/bin/activate

pip install -r requirements.txt
```

## Como rodar

```bash
python main.py                       # aplicação (em desenvolvimento)
python demo_processamento.py foto.jpg [segunda.jpg] [--canal R]
python -m pytest                     # testes do processamento
```

O `demo_processamento.py` gera um mosaico com todos os filtros e operações aplicados à foto e o salva em `saidas/mosaico.png`. Sem a segunda imagem, as operações usam a própria foto espelhada.

## Estrutura

```
editor/
  contrato.py      classes Filtro, Operacao e Passo (interface entre as partes)
  filtros.py       os 12 filtros
  operacoes.py     as 4 operações entre duas imagens
  pipeline.py      aplicar_pipeline(): aplica a lista de passos sobre a original
assets/
  stickers/        PNGs com canal alfa
  imagens/         imagens de exemplo
tests/             testes automatizados do processamento
main.py            aplicação: modos, menu, trackbar, stickers (em desenvolvimento)
```

A aplicação guarda o que o usuário fez como uma lista de `Passo` e, a cada frame (ou a cada alteração, no modo foto), chama `aplicar_pipeline(original, passos)`. Por isso **Resetar** é só esvaziar a lista, e a imagem original nunca é alterada.

## Filtros

Ao selecionar um filtro, a aplicação mostra a descrição dele (`filtro.ajuda()`) antes de aplicar.

| # | Filtro | Categoria | Parâmetro |
|---|--------|-----------|-----------|
| 0 | Escala de cinza | intensidade | — |
| 1 | Negativo | intensidade | — |
| 2 | Sépia | cor | intensidade (0–100%) |
| 3 | Brilho | intensidade | nível (0–200, 100 = original) |
| 4 | Box blur | suavização | tamanho do kernel (1–31) |
| 5 | Gaussian blur | suavização | tamanho do kernel (1–31) |
| 6 | Mediana | suavização | tamanho do kernel (1–31) |
| 7 | Sharpen | realce | intensidade (0–30) |
| 8 | Laplaciano | realce / bordas | ganho (1–10) |
| 9 | Sobel | bordas | direção (0 = Gx, 1 = Gy, 2 = magnitude) |
| 10 | Canny | bordas | limiar inferior (0–255) |
| 11 | Limiarização | segmentação | limiar (0–255) |

Os kernels do Box blur, Sharpen, Laplaciano e Sobel são montados à mão em `editor/filtros.py` e aplicados com `cv2.filter2D`, então dá para ver a máscara de convolução usada em cada um.

### Seleção de canal

Cada filtro pode ser aplicado à imagem inteira ou a um único canal (R, G ou B). Com um canal selecionado, o filtro recebe só aquele canal e a tela mostra o resultado dele em tons de cinza.

## Operações com duas imagens

A segunda imagem é redimensionada automaticamente para o tamanho da primeira. As contas são feitas em ponto flutuante e saturadas em [0, 255].

| # | Operação | Fórmula | Parâmetro |
|---|----------|---------|-----------|
| 0 | Adição | A + B | — |
| 1 | Subtração ponderada | A − w·B | peso de B (0–100%) |
| 2 | Blending | α·A + (1 − α)·B | alfa (0–100%) |
| 3 | Diferença absoluta | \|A − B\| | — |

## Teclas

*(a definir junto com a aplicação)*

## Extras implementados

- **Combinação de filtros:** cada filtro ou operação é aplicado sobre o resultado do anterior, em qualquer quantidade e ordem.

## Referências

- GONZALEZ, R. C.; WOODS, R. E. *Digital Image Processing*. Pearson, 2018.
- [Documentação do OpenCV](https://docs.opencv.org/4.x/)
