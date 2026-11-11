"""Resumo agregado em JSON: a ÚNICA entrada do texto de insights (por regras hoje, LLM depois).

Nunca leva linhas de venda nem dado pessoal: só totais e as primeiras posições de cada lista.
Os números já saem arredondados como aparecem na tela, para o verificador conferir o texto.
"""
import math

from dashnator.analyses.perdidas import DEVOLUCAO
from dashnator.core.importer import Dataset

TOP = 10


def _r(v, casas: int = 0):
    """Arredonda para o que a tela mostra; vazio vira None."""
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return None
    return int(round(v)) if casas == 0 else round(float(v), casas)


def _texto(v) -> str:
    return "" if v is None or v != v else str(v)


def montar_payload(ds: Dataset, cfg: dict, res: dict) -> dict:
    k, parado, ruptura = res["kpis"], res["parado"], res["ruptura"]
    perdidas, orc = res["perdidas"], res["orcamentos"]

    payload = {
        "loja": ds.nome_loja,
        "nicho": cfg.get("rotulo", cfg.get("nome", "")),
        "periodo": {"dados_ate": ds.fim.strftime("%d/%m/%Y"), "dias_de_historico": ds.dias_historico,
                    "dias_dos_indicadores": k["dias"],
                    "historico_minimo_dias": cfg["min_historico_dias"],
                    "historico_suficiente": ds.dias_historico >= cfg["min_historico_dias"]},
        "config": {"janela_venda_dias": cfg["janela_venda_dias"], "encalhe_dias": cfg["encalhe_dias"],
                   "prazo_padrao_dias": cfg["lead_time_dias"],
                   "margem_seguranca_dias": cfg["margem_seguranca_dias"],
                   "cobertura_alvo_dias": cfg["cobertura_alvo_dias"],
                   "corte_abc_pct": [_r(c * 100, 1) for c in cfg["corte_abc"]]},
        "kpis": {
            "faturamento_12m": _r(k["faturamento"]),
            "vendas": k["vendas"],
            "ticket_medio": _r(k["ticket_medio"]),
            "margem_pct": _r(k["margem"] * 100, 1) if k["margem"] is not None else None,
            "dinheiro_parado": _r(parado["total"]),
            "pct_parado": _r(parado["pct_do_estoque"] * 100, 1),
            "itens_parados": parado["itens"],
            "valor_sempre_mantenho": _r(parado["valor_sempre_mantenho"]),
            "itens_em_risco": ruptura["itens"],
            "venda_em_risco": _r(ruptura["venda_em_risco"]),
            "compra_sugerida": _r(ruptura["compra_sugerida"]),
        },
        "parado_top": [
            {"sku": r.sku, "descricao": r.descricao, "categoria": _texto(getattr(r, "categoria", "")),
             "quantidade": _r(r.quantidade_atual), "valor": _r(r.valor_parado),
             "dias_sem_venda": _r(r.dias_sem_venda)}
            for r in res["parado_itens"].head(TOP).itertuples()],
        "parado_por_categoria": [
            {"categoria": _texto(r.categoria), "valor": _r(r.valor_parado), "itens": int(r.itens)}
            for r in parado["por_categoria"].head(6).itertuples()],
        "ruptura_top": [
            {"sku": r.sku, "descricao": r.descricao, "classe": r.classe, "estoque": _r(r.quantidade_atual),
             "dias_de_estoque": _r(r.cobertura_dias, 1), "venda_por_dia": _r(r.venda_diaria, 2),
             "comprar": int(r.qtd_sugerida), "custo_da_compra": _r(r.valor_compra),
             "venda_em_risco": _r(r.venda_em_risco)}
            for r in res["ruptura_itens"].head(TOP).itertuples()],
        "abc": [
            {"classe": classe, "itens": int(r.itens), "pct_itens": _r(r.pct_itens * 100, 1),
             "faturamento": _r(r.faturamento), "pct_faturamento": _r(r.pct_valor * 100, 1)}
            for classe, r in zip(res["resumo_abc"].index, res["resumo_abc"].itertuples())],
        "avisos": list(ds.avisos),
    }

    if res["dia_hora"]:
        payload["horarios_de_pico"] = [{"dia": t["dia"], "hora": t["hora"], "valor": _r(t["valor"])}
                                       for t in res["dia_hora"]["top"]]
    if perdidas:
        dev = perdidas["devolucoes_por_fornecedor"]
        payload["kpis"]["perdidas_registros"] = perdidas["ocorrencias"]
        payload["kpis"]["perdidas_valor"] = _r(perdidas["valor_estimado"])
        payload["perdidas"] = {
            "por_motivo": [{"motivo": r.motivo, "rotulo": r.rotulo, "casos": int(r.casos)}
                           for r in perdidas["por_motivo"].itertuples()],
            "top": [{"sku": _texto(r.sku), "descricao": r.descricao, "vezes": int(r.ocorrencias),
                     "quantidade": _r(r.quantidade), "valor": _r(r.valor)}
                    for r in perdidas["ranking"].head(TOP).itertuples()],
            "devolucoes": perdidas["devolucoes"],
            "devolucoes_valor": _r(perdidas["valor_devolucoes"]),
            "devolucoes_por_fornecedor": [{"fornecedor": r.fornecedor, "casos": int(r.casos)}
                                          for r in dev.head(5).itertuples()],
            "motivo_devolucao": DEVOLUCAO,
        }
    if orc:
        payload["kpis"]["orcamentos"] = orc["orcamentos"]
        payload["kpis"]["conversao_pct"] = _r(orc["taxa"] * 100, 1)
        payload["kpis"]["orcamentos_nao_convertidos_valor"] = _r(orc["valor_nao_convertido"])
        payload["orcamentos"] = {
            "por_vendedor": ([] if orc["por_vendedor"] is None else
                             [{"vendedor": r.vendedor, "orcamentos": int(r.orcamentos),
                               "conversao_pct": _r(r.taxa * 100, 1)} for r in orc["por_vendedor"].itertuples()]),
            "top_nao_convertidos": [{"sku": r.sku, "descricao": r.descricao, "vezes": int(r.vezes),
                                     "valor": _r(r.valor)}
                                    for r in orc["top_nao_convertidos"].head(TOP).itertuples()],
        }
    return payload
