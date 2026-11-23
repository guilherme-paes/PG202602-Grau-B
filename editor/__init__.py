"""Editor de imagens e vídeo — Processamento Gráfico, Grau B.

Uso na aplicação:
    from editor import FILTROS, OPERACOES, CANAIS, Passo, aplicar_pipeline
"""

from .contrato import CANAIS, Filtro, Operacao, Passo
from .filtros import FILTROS
from .operacoes import OPERACOES
from .pipeline import aplicar_passo, aplicar_pipeline

__all__ = [
    "CANAIS",
    "FILTROS",
    "OPERACOES",
    "Filtro",
    "Operacao",
    "Passo",
    "aplicar_passo",
    "aplicar_pipeline",
]
