"""Risco de faltar e sugestão de compra, para as classes A e B.

venda_diaria   = quantidade vendida na janela ÷ dias da janela
cobertura_dias = estoque ÷ venda_diaria
risco          = cobertura < prazo do fornecedor + margem de segurança
qtd_sugerida   = arredonda_para_cima(max(0, venda_diaria × (prazo + cobertura_alvo) − estoque))
venda_em_risco = max(0, prazo − cobertura) × venda_diaria × preço de venda

Limitação: sem histórico diário de estoque, dias em que o item já faltou puxam a venda diária para baixo.
"""
import math

import pandas as pd

from dashnator.core.periodo import na_janela


def risco_ruptura(estoque: pd.DataFrame, vendas: pd.DataFrame, abc: pd.DataFrame, janela: int = 90,
                  lead: float = 7, seguranca: float = 3, alvo: float = 30) -> tuple[pd.DataFrame, dict]:
    vendido = na_janela(vendas, janela).groupby("sku")["quantidade"].sum()
    e = estoque.copy()
    e["classe"] = e["sku"].map(abc.set_index("sku")["classe"])
    e["venda_diaria"] = e["sku"].map(vendido).fillna(0.0) / janela
    e = e[e["classe"].isin(["A", "B"]) & (e["venda_diaria"] > 0)].copy()

    prazo = e["lead_time_dias"] if "lead_time_dias" in e else pd.Series(float("nan"), index=e.index)
    e["prazo_dias"] = prazo.astype(float).fillna(float(lead))
    e["cobertura_dias"] = e["quantidade_atual"] / e["venda_diaria"]
    e = e[e["cobertura_dias"] < e["prazo_dias"] + seguranca].copy()

    falta = (e["venda_diaria"] * (e["prazo_dias"] + alvo) - e["quantidade_atual"]).clip(lower=0)
    e["qtd_sugerida"] = falta.map(lambda x: int(math.ceil(x - 1e-9))).astype(int)
    e["valor_compra"] = e["qtd_sugerida"] * e["custo_unitario"]
    e["venda_em_risco"] = ((e["prazo_dias"] - e["cobertura_dias"]).clip(lower=0)
                           * e["venda_diaria"] * e["preco_venda"])

    colunas = [c for c in ("sku", "descricao", "categoria", "fornecedor", "classe", "quantidade_atual",
                           "venda_diaria", "cobertura_dias", "prazo_dias", "qtd_sugerida", "custo_unitario",
                           "valor_compra", "venda_em_risco") if c in e]
    itens = (e[colunas].sort_values(["venda_em_risco", "valor_compra", "sku"], ascending=[False, False, True])
             .reset_index(drop=True))
    resumo = {
        "itens": int(len(itens)),
        "compra_sugerida": float(itens["valor_compra"].sum()),
        "venda_em_risco": float(itens["venda_em_risco"].sum()),
        "janela": janela, "prazo_padrao": lead, "seguranca": seguranca, "alvo": alvo,
    }
    return itens, resumo
