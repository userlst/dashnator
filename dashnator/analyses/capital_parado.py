"""Dinheiro parado: item com estoque e sem venda há N dias ou mais, valorizado a custo.

Itens marcados como 'sempre mantenho' ficam fora dos alertas (o valor deles é informado à parte).
Item que nunca vendeu só é acusado quando o histórico de vendas cobre os N dias.
"""
import pandas as pd

from dashnator.core.periodo import dias_de_historico, fim_data


def capital_parado(estoque: pd.DataFrame, vendas: pd.DataFrame, dias: int = 180) -> tuple[pd.DataFrame, dict]:
    fim = fim_data(vendas)
    historico_suficiente = dias_de_historico(vendas) >= dias
    ultima = vendas.groupby("sku")["data_hora"].max().dt.normalize()

    e = estoque.copy()
    e["valor_parado"] = e["quantidade_atual"] * e["custo_unitario"]
    e["ultima_venda"] = e["sku"].map(ultima)
    e["dias_sem_venda"] = (fim - e["ultima_venda"]).dt.days
    e["nunca_vendeu"] = e["ultima_venda"].isna()
    parado = (e["quantidade_atual"] > 0) & (
        (e["dias_sem_venda"] >= dias) | (e["nunca_vendeu"] & historico_suficiente))
    mantenho = (e["sempre_mantenho"].astype(bool) if "sempre_mantenho" in e
                else pd.Series(False, index=e.index))

    colunas = [c for c in ("sku", "descricao", "categoria", "fornecedor", "quantidade_atual", "custo_unitario",
                           "valor_parado", "dias_sem_venda", "nunca_vendeu") if c in e]
    itens = (e[parado & ~mantenho][colunas]
             .sort_values(["valor_parado", "sku"], ascending=[False, True]).reset_index(drop=True))

    total = float(itens["valor_parado"].sum())
    valor_estoque = float(e["valor_parado"].sum())

    def por(coluna):
        if coluna not in itens or itens.empty:
            return pd.DataFrame(columns=[coluna, "valor_parado", "itens"])
        return (itens.groupby(coluna, as_index=False)
                     .agg(valor_parado=("valor_parado", "sum"), itens=("sku", "count"))
                     .sort_values("valor_parado", ascending=False).reset_index(drop=True))

    resumo = {
        "total": total,
        "itens": int(len(itens)),
        "pct_do_estoque": total / valor_estoque if valor_estoque else 0.0,
        "valor_estoque": valor_estoque,
        "valor_sempre_mantenho": float(e.loc[parado & mantenho, "valor_parado"].sum()),
        "historico_suficiente": bool(historico_suficiente),
        "dias": dias,
        "por_categoria": por("categoria"),
        "por_fornecedor": por("fornecedor"),
    }
    return itens, resumo
