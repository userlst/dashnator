"""Giro e dias de estoque por categoria, marca ou fornecedor.

giro_anual     = venda a custo anualizada ÷ valor do estoque atual
cobertura_dias = valor do estoque atual ÷ venda a custo por dia
Aproximação da v1: usa o estoque de hoje no lugar do estoque médio do período.
"""
import pandas as pd

from dashnator.core.periodo import dias_de_historico, na_janela


def giro_por(estoque: pd.DataFrame, vendas: pd.DataFrame, por: str = "categoria", dias: int = 365) -> pd.DataFrame:
    if por not in estoque:
        return pd.DataFrame(columns=[por, "estoque_custo", "cmv_anual", "giro_anual", "cobertura_dias"])
    dias_usados = max(1, min(dias, dias_de_historico(vendas)))
    v = na_janela(vendas, dias_usados)
    custo_cadastro = estoque.set_index("sku")["custo_unitario"]
    custo = v["sku"].map(custo_cadastro)
    if "custo_unitario" in v:
        custo = v["custo_unitario"].fillna(custo)
    v = v.assign(cmv=v["quantidade"] * custo.fillna(0.0), grupo=v["sku"].map(estoque.set_index("sku")[por]))

    e = estoque.assign(estoque_custo=estoque["quantidade_atual"] * estoque["custo_unitario"])
    g = e.groupby(por)["estoque_custo"].sum().to_frame()
    g["cmv_anual"] = (v.groupby("grupo")["cmv"].sum() * 365 / dias_usados).reindex(g.index).fillna(0.0)
    g["giro_anual"] = (g["cmv_anual"] / g["estoque_custo"]).where(g["estoque_custo"] > 0)
    g["cobertura_dias"] = (g["estoque_custo"] / (g["cmv_anual"] / 365)).where(g["cmv_anual"] > 0)
    return g.sort_values("estoque_custo", ascending=False).reset_index()
