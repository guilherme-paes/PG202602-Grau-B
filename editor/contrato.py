"""Contrato entre o processamento (Pessoa 1) e a aplicação (Pessoa 2).

Pessoa 1 expõe (em editor/):
    FILTROS, OPERACOES             -> listas de Filtro / Operacao
    aplicar_pipeline(original, passos) -> imagem BGR uint8

Pessoa 2 expõe:
    colar_sticker(imagem, sticker_bgra, x, y) -> imagem

Fluxo esperado na aplicação: a cada frame (ou a cada mudança, no modo foto)
    resultado = aplicar_pipeline(original, passos)
e, no modo foto, os stickers são colados por cima do resultado. Assim eles não
são afetados pelos filtros, e "Resetar" é só esvaziar a lista de passos.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import numpy as np

# Opções de canal na ordem em que fazem sentido para o usuário.
CANAIS = ("todos", "R", "G", "B")


@dataclass
class Filtro:
    nome: str
    descricao: str  # o que faz + o que o parâmetro controla (exibida ao SELECIONAR)
    aplicar: Callable[[np.ndarray, int], np.ndarray]  # (imagem, param) -> imagem
    param_nome: str = ""  # "" se não tem parâmetro
    param_min: int = 0
    param_max: int = 0
    param_padrao: int = 0

    @property
    def tem_param(self) -> bool:
        return bool(self.param_nome)

    def ajuda(self) -> str:
        """Texto pronto para mostrar no console quando o usuário seleciona o efeito."""
        texto = f"[{self.nome}] {self.descricao}"
        if self.tem_param:
            texto += (
                f"\n  Parâmetro: {self.param_nome} "
                f"(de {self.param_min} a {self.param_max}, padrão {self.param_padrao})"
            )
        else:
            texto += "\n  Sem parâmetros."
        return texto


@dataclass
class Operacao(Filtro):
    """Igual a Filtro, mas `aplicar` recebe duas imagens do mesmo tamanho."""

    aplicar: Callable[[np.ndarray, np.ndarray, int], np.ndarray]  # (a, b, param) -> imagem


@dataclass
class Passo:
    """Uma ação que o usuário aplicou. A lista de passos é o histórico de edição."""

    tipo: str  # "filtro" ou "operacao"
    indice: int  # posição em FILTROS ou OPERACOES
    canal: str = "todos"  # um dos valores de CANAIS
    param: int | None = None  # None = usa o param_padrao do efeito
    imagem_b: np.ndarray | None = None  # segunda imagem (obrigatória em operações)
