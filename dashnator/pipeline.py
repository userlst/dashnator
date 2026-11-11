"""Roda todas as análises sobre o conjunto de dados da loja e devolve um dicionário de resultados.

É o único caminho de cálculo: relatório HTML, painel e texto de insights leem daqui.
"""
from dashnator.analyses.abc import curva_abc, resumo_abc
from dashnator.analyses.capital_parado import capital_parado
from dashnator.analyses.dia_hora import desempenho_vendedores, dia_hora
from dashnator.analyses.giro import giro_por
from dashnator.analyses.perdidas import conversao_orcamentos, vendas_perdidas
from dashnator.analyses.ruptura import risco_ruptura
from dashnator.core.importer import Dataset
from dashnator.core.periodo import na_janela

DIAS_KPIS = 365


def _kpis(ds: Dataset) -> dict:
    dias = min(DIAS_KPIS, ds.dias_historico)
    v = na_janela(ds.vendas, DIAS_KPIS, ds.fim)
    valor = v["quantidade"] * v["preco_unitario"]
    faturamento = float(valor.sum())
    vendas = int(v["documento"].nunique())
    margem = None
    if "custo_unitario" in v:
        com_custo = v["custo_unitario"].notna()
        base = float(valor[com_custo].sum())
        if base > 0:
            margem = 1 - float((v["quantidade"] * v["custo_unitario"])[com_custo].sum()) / base
    return {"dias": dias, "faturamento": faturamento, "vendas": vendas,
            "ticket_medio": faturamento / vendas if vendas else 0.0, "margem": margem}


def rodar(ds: Dataset, cfg: dict) -> dict:
    abc = curva_abc(ds.vendas, dias=DIAS_KPIS, cortes=tuple(cfg["corte_abc"]))
    parado_itens, parado = capital_parado(ds.estoque, ds.vendas, dias=cfg["encalhe_dias"])
    ruptura_itens, ruptura = risco_ruptura(
        ds.estoque, ds.vendas, abc, janela=cfg["janela_venda_dias"], lead=cfg["lead_time_dias"],
        seguranca=cfg["margem_seguranca_dias"], alvo=cfg["cobertura_alvo_dias"])
    return {
        "kpis": _kpis(ds),
        "abc": abc,
        "resumo_abc": resumo_abc(abc),
        "parado_itens": parado_itens,
        "parado": parado,
        "ruptura_itens": ruptura_itens,
        "ruptura": ruptura,
        "giro": {por: giro_por(ds.estoque, ds.vendas, por=por, dias=DIAS_KPIS)
                 for por in ("categoria", "fornecedor", "marca")},
        "dia_hora": dia_hora(ds.vendas),
        "vendedores": desempenho_vendedores(na_janela(ds.vendas, DIAS_KPIS, ds.fim)),
        "orcamentos": conversao_orcamentos(ds.orcamentos, ds.estoque),
        "perdidas": vendas_perdidas(ds.perdidas, ds.estoque, cfg.get("motivos_perdida", {})),
    }
