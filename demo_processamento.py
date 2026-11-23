"""Mosaico com todos os filtros e operações aplicados a uma imagem.

Serve para conferir o processamento sem depender da aplicação principal.

    python demo_processamento.py foto.jpg [segunda.jpg] [--canal R]

Sem a segunda imagem, as operações usam a própria foto espelhada.
O mosaico é salvo em saidas/mosaico.png e exibido numa janela.
"""

import sys
from pathlib import Path

import cv2
import numpy as np

from editor import CANAIS, FILTROS, OPERACOES, Passo, aplicar_pipeline

LADO = 260  # largura de cada quadro do mosaico
COLUNAS = 6


def _quadro(img, titulo):
    altura = round(img.shape[0] * LADO / img.shape[1])
    q = cv2.resize(img, (LADO, altura), interpolation=cv2.INTER_AREA)
    cv2.rectangle(q, (0, 0), (LADO, 22), (0, 0, 0), -1)
    cv2.putText(q, titulo, (5, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
    return q


def gerar_mosaico(original, segunda, canal="todos"):
    quadros = [_quadro(original, "Original")]
    for i, f in enumerate(FILTROS):
        saida = aplicar_pipeline(original, [Passo("filtro", i, canal)])
        quadros.append(_quadro(saida, f.nome))
    for i, op in enumerate(OPERACOES):
        saida = aplicar_pipeline(original, [Passo("operacao", i, canal, imagem_b=segunda)])
        quadros.append(_quadro(saida, op.nome))

    vazio = np.zeros_like(quadros[0])
    quadros += [vazio] * (-len(quadros) % COLUNAS)
    linhas = [np.hstack(quadros[i : i + COLUNAS]) for i in range(0, len(quadros), COLUNAS)]
    return np.vstack(linhas)


def main():
    args = sys.argv[1:]
    canal = "todos"
    if "--canal" in args:
        pos = args.index("--canal")
        canal = args[pos + 1]
        del args[pos : pos + 2]
    if not args or canal not in CANAIS:
        sys.exit(__doc__)

    original = cv2.imread(args[0])
    if original is None:
        sys.exit(f"Não consegui abrir {args[0]}")
    segunda = cv2.imread(args[1]) if len(args) > 1 else cv2.flip(original, 1)
    if segunda is None:
        sys.exit(f"Não consegui abrir {args[1]}")

    mosaico = gerar_mosaico(original, segunda, canal)
    Path("saidas").mkdir(exist_ok=True)
    cv2.imwrite("saidas/mosaico.png", mosaico)
    print("Salvo em saidas/mosaico.png")

    cv2.imshow("Mosaico (qualquer tecla fecha)", mosaico)
    cv2.waitKey(0)
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
