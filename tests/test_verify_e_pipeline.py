import pandas as pd

from dashnator.ai import template_insights
from dashnator.ai.payload import montar_payload
from dashnator.ai.verify import numeros_nao_verificados, textos_do_insight
from dashnator.config import carregar_nicho
from dashnator.core.importer import carregar_dataset
from dashnator.demo.generate import gerar_dados
from dashnator.pipeline import rodar
from dashnator.report.html import render


def test_verificador_aceita_numeros_do_payload_e_barra_os_inventados():
    payload = {"total": 1234567, "pct": 25.2, "itens": [{"descricao": "Filtro - Aplic. V07", "qtd": 12}]}
    assert numeros_nao_verificados("R$ 1.234.567 parados; 25,2% do estoque; 12 un. do Filtro Aplic. V07", payload) == []
    assert numeros_nao_verificados("R$ 999.999 parados", payload) == ["999.999"]
    assert numeros_nao_verificados("25,3% do estoque", payload) == ["25,3"]


def test_demo_de_ponta_a_ponta():
    """Dados fictícios -> importador -> análises -> insights -> HTML, com o texto 100% verificável."""
    dados = gerar_dados(n_skus=200, docs_por_dia=15.0)
    ds = carregar_dataset(dados["vendas"], dados["estoque"], dados["orcamentos"], dados["perdidas"], nome_loja="Loja Teste")
    cfg = carregar_nicho("autopecas")
    res = rodar(ds, cfg)
    payload = montar_payload(ds, cfg, res)
    ins = template_insights.gerar(payload)

    assert 1 <= len(ins["alertas"]) <= 5
    assert [a["impacto_reais"] for a in ins["alertas"]] == sorted((a["impacto_reais"] for a in ins["alertas"]), reverse=True)
    assert numeros_nao_verificados(textos_do_insight(ins), payload) == []

    # os números do payload batem com um cálculo independente direto das vendas
    v = ds.vendas
    ult = v[v["data_hora"].dt.normalize() > ds.fim - pd.Timedelta(days=365)]
    assert payload["kpis"]["faturamento_12m"] == round((ult["quantidade"] * ult["preco_unitario"]).sum())
    assert payload["kpis"]["vendas"] == ult["documento"].nunique()

    pagina = render(ds, cfg, res, ins, demo=True)
    assert pagina.startswith("<!doctype html>") and "Dados de demonstração" in pagina and "Loja Teste" in pagina
    assert "<script src" not in pagina and "http://" not in pagina and "https://" not in pagina  # autossuficiente


def test_pii_nao_chega_ao_payload():
    dados = gerar_dados(n_skus=200, docs_por_dia=8.0)
    vendas = dados["vendas"].assign(**{"Nome do Cliente": "João da Silva", "CPF": "111.222.333-44"})
    ds = carregar_dataset(vendas, dados["estoque"])
    cfg = carregar_nicho("autopecas")
    texto = str(montar_payload(ds, cfg, rodar(ds, cfg)))
    assert "João da Silva" not in texto and "111.222.333-44" not in texto
    assert any("CPF" in a for a in ds.avisos)
