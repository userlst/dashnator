"""Datas de referência. Toda análise usa a data da última venda, nunca "hoje"."""
import pandas as pd


def fim_data(vendas: pd.DataFrame) -> pd.Timestamp:
    """Data (sem hora) da última venda: a data de referência de todas as análises."""
    return vendas["data_hora"].max().normalize()


def inicio_data(vendas: pd.DataFrame) -> pd.Timestamp:
    return vendas["data_hora"].min().normalize()


def dias_de_historico(vendas: pd.DataFrame) -> int:
    """Do primeiro ao último dia com venda, contando os dois."""
    return int((fim_data(vendas) - inicio_data(vendas)).days) + 1


def na_janela(vendas: pd.DataFrame, dias: int, fim: pd.Timestamp | None = None) -> pd.DataFrame:
    """Vendas dos últimos `dias` dias até a data de referência (inclusive)."""
    fim = fim_data(vendas) if fim is None else fim
    return vendas[vendas["data_hora"].dt.normalize() > fim - pd.Timedelta(days=dias)]
