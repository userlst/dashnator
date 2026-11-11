"""Vendas perdidas, devoluções por incompatibilidade e orçamentos que não viraram venda."""
import pandas as pd

DEVOLUCAO = "devolucao_incompatibilidade"


def conversao_orcamentos(orcamentos: pd.DataFrame | None, estoque: pd.DataFrame, top: int = 15) -> dict | None:
    """Taxa de conversão (por orçamento, não por linha), por vendedor, e os itens mais orçados e não vendidos."""
    if orcamentos is None or orcamentos.empty:
        return None
    o = orcamentos.assign(valor=orcamentos["quantidade"] * orcamentos["preco_unitario"])
    docs = o.groupby("documento").agg(convertido=("convertido", "any"), valor=("valor", "sum"))
    total, convertidos = int(len(docs)), int(docs["convertido"].sum())
    nao = o[~o["convertido"].astype(bool)]

    por_vendedor = None
    if "vendedor" in o and o["vendedor"].notna().any():
        dv = o.groupby("documento").agg(vendedor=("vendedor", "first"), convertido=("convertido", "any"))
        por_vendedor = (dv.groupby("vendedor").agg(orcamentos=("convertido", "size"), convertidos=("convertido", "sum"))
                        .assign(taxa=lambda d: d["convertidos"] / d["orcamentos"])
                        .sort_values("taxa", ascending=False).reset_index())

    descricao = estoque.set_index("sku")["descricao"]
    top_nao = (nao.groupby("sku").agg(vezes=("documento", "nunique"), quantidade=("quantidade", "sum"),
                                      valor=("valor", "sum"))
               .sort_values(["vezes", "valor"], ascending=False).head(top).reset_index())
    top_nao["descricao"] = top_nao["sku"].map(descricao).fillna(top_nao["sku"])
    return {
        "orcamentos": total,
        "convertidos": convertidos,
        "taxa": convertidos / total if total else 0.0,
        "valor_nao_convertido": float(nao["valor"].sum()),
        "por_vendedor": por_vendedor,
        "top_nao_convertidos": top_nao,
    }


def vendas_perdidas(perdidas: pd.DataFrame | None, estoque: pd.DataFrame, motivos: dict, top: int = 10) -> dict | None:
    """Ranking do que o cliente pediu e não levou. Valor estimado = quantidade × preço de venda do cadastro
    (peça sem cadastro entra na contagem, com valor zero)."""
    if perdidas is None or perdidas.empty:
        return None
    cadastro = estoque.set_index("sku")
    p = perdidas.copy()
    p["valor"] = p["quantidade"] * p["sku"].map(cadastro["preco_venda"]).fillna(0.0)
    p["item"] = p["sku"].fillna(p["descricao"])

    ranking = (p.groupby("item", sort=False)
                 .agg(sku=("sku", "first"), descricao=("descricao", "first"), ocorrencias=("item", "size"),
                      quantidade=("quantidade", "sum"), valor=("valor", "sum"))
                 .sort_values(["valor", "ocorrencias"], ascending=False).head(top).reset_index(drop=True))

    por_motivo = (p.groupby("motivo").size().rename("casos").sort_values(ascending=False).reset_index())
    por_motivo["rotulo"] = por_motivo["motivo"].map(lambda m: motivos.get(m, str(m).replace("_", " ").capitalize()))

    devolucoes = p[p["motivo"] == DEVOLUCAO]
    fornecedor = devolucoes["sku"].map(cadastro["fornecedor"]) if "fornecedor" in cadastro else pd.Series(dtype="string")
    if "fornecedor" in devolucoes:
        fornecedor = devolucoes["fornecedor"].fillna(fornecedor)
    por_fornecedor = (fornecedor.dropna().value_counts().rename_axis("fornecedor").rename("casos").reset_index())
    return {
        "ocorrencias": int(len(p)),
        "valor_estimado": float(p["valor"].sum()),
        "por_motivo": por_motivo,
        "ranking": ranking,
        "devolucoes": int(len(devolucoes)),
        "valor_devolucoes": float(devolucoes["valor"].sum()),
        "devolucoes_por_fornecedor": por_fornecedor,
    }
