"""Curva ABC por faturamento. A até 80% do acumulado, B até 95%, C o resto.

O item que cruza o corte fica na classe de cima: vale o acumulado ANTES dele.
"""
import pandas as pd

from dashnator.core.periodo import na_janela


def curva_abc(vendas: pd.DataFrame, dias: int = 365, cortes=(0.80, 0.95)) -> pd.DataFrame:
    """Uma linha por SKU, do maior faturamento para o menor, com a classe."""
    v = na_janela(vendas, dias)
    v = v.assign(faturamento=v["quantidade"] * v["preco_unitario"])
    abc = (v.groupby("sku", as_index=False)
             .agg(descricao=("descricao", "first"), quantidade=("quantidade", "sum"),
                  faturamento=("faturamento", "sum"))
             .sort_values(["faturamento", "sku"], ascending=[False, True], kind="mergesort")
             .reset_index(drop=True))
    total = abc["faturamento"].sum()
    acumulado = abc["faturamento"].cumsum()
    antes = acumulado - abc["faturamento"]
    folga = total * 1e-12
    abc["pct"] = abc["faturamento"] / total if total else 0.0
    abc["pct_acumulado"] = acumulado / total if total else 0.0
    abc["classe"] = "C"
    abc.loc[antes < cortes[1] * total - folga, "classe"] = "B"
    abc.loc[antes < cortes[0] * total - folga, "classe"] = "A"
    return abc


def resumo_abc(abc: pd.DataFrame) -> pd.DataFrame:
    """Por classe: quantos itens, % dos itens, faturamento e % do faturamento."""
    r = (abc.groupby("classe").agg(itens=("sku", "count"), faturamento=("faturamento", "sum"))
            .reindex(["A", "B", "C"], fill_value=0))
    r["pct_itens"] = r["itens"] / max(len(abc), 1)
    total = abc["faturamento"].sum()
    r["pct_valor"] = r["faturamento"] / total if total else 0.0
    return r
