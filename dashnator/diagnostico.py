"""Do conjunto de dados ao diagnóstico pronto: análises, payload e texto verificado.

Relatório, linha de comando e painel chamam `diagnosticar`: um caminho só para os números.
"""
from dataclasses import dataclass

from dashnator.ai import template_insights
from dashnator.ai.payload import montar_payload
from dashnator.ai.verify import numeros_nao_verificados, textos_do_insight
from dashnator.core.importer import Dataset
from dashnator.pipeline import rodar


@dataclass
class Diagnostico:
    ds: Dataset
    cfg: dict
    res: dict        # resultados das análises (tabelas completas)
    payload: dict    # resumo agregado: a única entrada do texto
    insights: dict   # resumo, alertas e oportunidades


def diagnosticar(ds: Dataset, cfg: dict) -> Diagnostico:
    res = rodar(ds, cfg)
    payload = montar_payload(ds, cfg, res)
    insights = template_insights.gerar(payload)
    fora = numeros_nao_verificados(textos_do_insight(insights), payload)
    if fora:  # nunca deveria acontecer com o texto por regras; se acontecer, é erro de código
        raise AssertionError(f"Texto com números fora do payload: {fora}")
    return Diagnostico(ds=ds, cfg=cfg, res=res, payload=payload, insights=insights)
