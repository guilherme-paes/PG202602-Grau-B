# PG202602-Grau-B

Protótipo de um editor de imagens e vídeo inspirado nos _stories_ do Instagram, desenvolvido para o Grau B de Processamento Gráfico (Unisinos). O usuário carrega uma foto (**Modo Foto**) ou abre a webcam (**Modo Vídeo**) e aplica filtros, operações entre duas imagens e _stickers_.

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
python main.py                       # aplicação
python main.py foto.jpg              # aplicação, já abrindo uma foto
python demo_processamento.py foto.jpg [segunda.jpg] [--canal R]
python -m pytest                     # testes (processamento e aplicação)
```

Fluxo básico da aplicação: abra uma foto (**O**) ou ligue a webcam (**V**), escolha um efeito com **A / D** (a descrição aparece no console), ajuste o parâmetro na trackbar (a prévia aparece na hora) e aperte **Enter** para aplicar. Os efeitos se acumulam, um sobre o resultado do anterior.

> Os menus de escolha de arquivo (**O** e **B**) funcionam no **console**: depois de apertar a tecla, digite o número da lista (arquivos de `assets/imagens/`) ou um caminho completo. As teclas só valem com a janela do OpenCV em foco.

O `demo_processamento.py` gera um mosaico com todos os filtros e operações aplicados à foto e o salva em `saidas/mosaico.png`. Sem a segunda imagem, as operações usam a própria foto espelhada.

## Estrutura

```
main.py            aplicação: ponto de entrada
app/
  aplicacao.py     loop principal, modos foto/vídeo, menu, trackbar, salvar/resetar
  stickers.py      leitura de stickers e composição alfa feita à mão
editor/
  contrato.py      classes Filtro, Operacao e Passo (interface entre as partes)
  filtros.py       os 12 filtros
  operacoes.py     as 4 operações entre duas imagens
  pipeline.py      aplicar_pipeline(): aplica a lista de passos sobre a original
assets/
  stickers/        PNGs com canal alfa
  imagens/         imagens de exemplo
tools/
  gerar_stickers.py  gera os PNGs de stickers
tests/             testes automatizados (processamento e aplicação)
saidas/            imagens salvas pelo programa (ignorada pelo git)
```

A aplicação guarda o que o usuário fez como uma lista de `Passo` e, a cada frame (ou a cada alteração, no modo foto), chama `aplicar_pipeline(original, passos)`. Por isso **Resetar** é só esvaziar a lista, e a imagem original nunca é alterada.

## Teclas

| Tecla               | Ação                                                                     |
| ------------------- | ------------------------------------------------------------------------ |
| `O`                 | Abrir foto                                                               |
| `V`                 | Ligar / desligar a webcam                                                |
| `A` / `D`           | Efeito anterior / próximo (exibe a descrição e o parâmetro no console)   |
| `C`                 | Alternar canal: todos → R → G → B                                        |
| Trackbar            | Parâmetro do efeito selecionado                                          |
| `Enter` ou `Espaço` | Confirmar: aplica o efeito selecionado                                   |
| `P`                 | Liga / desliga a prévia do efeito selecionado                            |
| `B`                 | Carregar a imagem B (segunda imagem das operações)                       |
| `Z`                 | Desfazer o último efeito aplicado                                        |
| `1`–`9`             | Escolher sticker (depois, clique na foto para colar); só no modo foto    |
| `0`                 | Desativar sticker                                                        |
| `+` / `-`           | Aumentar / diminuir o sticker                                            |
| `U`                 | Remover o último sticker colado                                          |
| `S`                 | Salvar em `saidas/` (nome com data e hora; no vídeo salva o frame atual) |
| `R`                 | Resetar: esvazia os efeitos e remove os stickers                         |
| `H`                 | Mostrar a ajuda de teclas no console                                     |
| `Q` ou `Esc`        | Sair                                                                     |

## Filtros

Ao selecionar um filtro, a aplicação mostra a descrição dele (`filtro.ajuda()`) antes de aplicar.

| #   | Filtro          | Categoria       | Parâmetro                               |
| --- | --------------- | --------------- | --------------------------------------- |
| 0   | Escala de cinza | intensidade     | —                                       |
| 1   | Negativo        | intensidade     | —                                       |
| 2   | Sépia           | cor             | intensidade (0–100%)                    |
| 3   | Brilho          | intensidade     | nível (0–200, 100 = original)           |
| 4   | Box blur        | suavização      | tamanho do kernel (1–31)                |
| 5   | Gaussian blur   | suavização      | tamanho do kernel (1–31)                |
| 6   | Mediana         | suavização      | tamanho do kernel (1–31)                |
| 7   | Sharpen         | realce          | intensidade (0–30)                      |
| 8   | Laplaciano      | realce / bordas | ganho (1–10)                            |
| 9   | Sobel           | bordas          | direção (0 = Gx, 1 = Gy, 2 = magnitude) |
| 10  | Canny           | bordas          | limiar inferior (0–255)                 |
| 11  | Limiarização    | segmentação     | limiar (0–255)                          |

Os kernels do Box blur, Sharpen, Laplaciano e Sobel são montados à mão em `editor/filtros.py` e aplicados com `cv2.filter2D`, então dá para ver a máscara de convolução usada em cada um.

### Seleção de canal

Cada filtro pode ser aplicado à imagem inteira ou a um único canal (R, G ou B). Com um canal selecionado, o filtro recebe só aquele canal e a tela mostra o resultado dele em tons de cinza.

## Operações com duas imagens

A segunda imagem é redimensionada automaticamente para o tamanho da primeira. As contas são feitas em ponto flutuante e saturadas em [0, 255].

| #   | Operação            | Fórmula         | Parâmetro          |
| --- | ------------------- | --------------- | ------------------ |
| 0   | Adição              | A + B           | —                  |
| 1   | Subtração ponderada | A − w·B         | peso de B (0–100%) |
| 2   | Blending            | α·A + (1 − α)·B | alfa (0–100%)      |
| 3   | Diferença absoluta  | \|A − B\|       | —                  |

## Stickers

Cinco PNGs com canal alfa em `assets/stickers/` (coração, estrela, óculos, coroa e sol). Eles só funcionam no Modo Foto: escolha o sticker com `1`–`5` e clique na foto para colá-lo centralizado no ponto do clique.

A composição é feita à mão em `app/stickers.py`, pixel a pixel:

```
saída = α · sticker + (1 − α) · fundo,   com α = A / 255
```

Funciona mesmo com o sticker parcialmente fora da imagem (só o trecho visível é composto). Os stickers são colados por cima do resultado dos filtros, então não são afetados por eles. Para gerar os PNGs de novo: `python -m tools.gerar_stickers`.

## Extras implementados

- **Combinação de filtros:** cada filtro ou operação é aplicado sobre o resultado do anterior, em qualquer quantidade e ordem.

## Observações

- Fotos com mais de 1280 px no maior lado são reduzidas ao abrir, para a edição ficar fluida.
- A imagem da webcam é espelhada, como em câmera frontal.
- O texto de status escrito na janela (modo, efeito, parâmetro) não vai para o arquivo salvo.

## Referências

- GONZALEZ, R. C.; WOODS, R. E. _Digital Image Processing_. Pearson, 2018.
- [Documentação do OpenCV](https://docs.opencv.org/4.x/)
