"""Formatação de números em pt-BR. Toda tela, relatório e texto de IA formata por aqui."""
import math


def _vazio(v) -> bool:
    return v is None or (isinstance(v, float) and math.isnan(v))


def inteiro(v) -> str:
    """1234567 -> '1.234.567'"""
    if _vazio(v):
        return "—"
    return f"{int(round(v)):,}".replace(",", ".")


def numero(v, casas: int = 1) -> str:
    """1234.56 -> '1.234,6'"""
    if _vazio(v):
        return "—"
    return f"{v:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def reais(v, centavos: bool = False) -> str:
    """1234.56 -> 'R$ 1.235' (ou 'R$ 1.234,56' com centavos)"""
    if _vazio(v):
        return "—"
    sinal = "-" if v < 0 else ""
    return f"{sinal}R$ {numero(abs(v), 2) if centavos else inteiro(abs(v))}"


def pct(v, casas: int = 1) -> str:
    """25.2 -> '25,2%'. O valor já vem em pontos percentuais."""
    if _vazio(v):
        return "—"
    return f"{numero(v, casas)}%"


def dias(v) -> str:
    """Dias de estoque com uma casa: 1.94 -> '1,9'"""
    return numero(v, 1)
