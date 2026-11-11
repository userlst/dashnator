"""Movimento por dia da semana e hora, e desempenho por vendedor (apoio à escala do balcão)."""
import pandas as pd

DIAS = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]


def dia_hora(vendas: pd.DataFrame, top: int = 3) -> dict | None:
    """Faturamento e número de vendas por dia da semana × hora. None se as vendas vieram sem hora."""
    if not (vendas["data_hora"] != vendas["data_hora"].dt.normalize()).any():
        return None
    v = vendas.assign(valor=vendas["quantidade"] * vendas["preco_unitario"],
                      dia=vendas["data_hora"].dt.day_of_week, hora=vendas["data_hora"].dt.hour)
    horas = list(range(int(v["hora"].min()), int(v["hora"].max()) + 1))
    # cada venda (documento) conta uma vez, na hora do primeiro item
    docs = v.groupby("documento").agg(dia=("dia", "first"), hora=("hora", "first"), valor=("valor", "sum"))

    def quadro(serie):
        return serie.unstack(fill_value=0).reindex(index=range(7), columns=horas, fill_value=0)

    faturamento = quadro(docs.groupby(["dia", "hora"])["valor"].sum()).astype(float)
    n_vendas = quadro(docs.groupby(["dia", "hora"]).size()).astype(int)
    maiores = faturamento.stack().sort_values(ascending=False, kind="mergesort").head(top)
    return {
        "horas": horas,
        "faturamento": faturamento,
        "vendas": n_vendas,
        "top": [{"dia": DIAS[d], "hora": int(h), "valor": float(valor)} for (d, h), valor in maiores.items()
                if valor > 0],
        "por_dia": faturamento.sum(axis=1).rename(index=dict(enumerate(DIAS))),
    }


def desempenho_vendedores(vendas: pd.DataFrame) -> pd.DataFrame | None:
    """Por vendedor: vendas, faturamento, ticket médio e itens por venda. None se não há a coluna."""
    if "vendedor" not in vendas or vendas["vendedor"].isna().all():
        return None
    v = vendas.assign(valor=vendas["quantidade"] * vendas["preco_unitario"])
    g = (v.groupby("vendedor").agg(vendas=("documento", "nunique"), faturamento=("valor", "sum"),
                                   linhas=("sku", "count")))
    g["ticket_medio"] = g["faturamento"] / g["vendas"]
    g["itens_por_venda"] = g["linhas"] / g["vendas"]
    return (g.drop(columns="linhas").sort_values("faturamento", ascending=False).reset_index())
