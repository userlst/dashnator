"""Testes com resposta conhecida: cada caso foi calculado à mão."""
import math

import pandas as pd
import pytest

from dashnator.analyses.abc import curva_abc, resumo_abc
from dashnator.analyses.capital_parado import capital_parado
from dashnator.analyses.dia_hora import desempenho_vendedores, dia_hora
from dashnator.analyses.giro import giro_por
from dashnator.analyses.perdidas import conversao_orcamentos, vendas_perdidas
from dashnator.analyses.ruptura import risco_ruptura

FIM = pd.Timestamp("2026-01-31")


def _vendas(linhas):
    """linhas: (data_hora, documento, sku, quantidade, preco_unitario[, vendedor])"""
    df = pd.DataFrame(linhas, columns=["data_hora", "documento", "sku", "quantidade", "preco_unitario"][: len(linhas[0])]
                      if len(linhas[0]) == 5 else ["data_hora", "documento", "sku", "quantidade", "preco_unitario", "vendedor"])
    df["data_hora"] = pd.to_datetime(df["data_hora"])
    df["descricao"] = "Item " + df["sku"]
    return df


def _estoque(linhas):
    """linhas: (sku, quantidade_atual, custo, preco_venda, lead_time ou None, sempre_mantenho)"""
    df = pd.DataFrame(linhas, columns=["sku", "quantidade_atual", "custo_unitario", "preco_venda", "lead_time_dias", "sempre_mantenho"])
    df["descricao"] = "Item " + df["sku"]
    df["categoria"], df["fornecedor"], df["marca"] = "Cat", "Forn", "Marca"
    df["lead_time_dias"] = df["lead_time_dias"].astype(float)
    return df


# ------------------------------------------------------------------ ABC
def test_abc_cinco_itens():
    # valores 50, 30, 10, 5, 5 -> acumulado 50, 80, 90, 95, 100
    v = _vendas([("2026-01-10", f"D{i}", s, 1, val) for i, (s, val) in enumerate(
        [("a", 50), ("b", 30), ("c", 10), ("d", 5), ("e", 5)])])
    abc = curva_abc(v)
    assert abc["sku"].tolist() == ["a", "b", "c", "d", "e"]
    assert abc["classe"].tolist() == ["A", "A", "B", "B", "C"]
    r = resumo_abc(abc)
    assert r["itens"].tolist() == [2, 2, 1]
    assert r.at["A", "pct_valor"] == pytest.approx(0.80)


def test_abc_item_que_cruza_o_corte_fica_na_classe_de_cima():
    # 70, 15, 15: o segundo leva o acumulado de 70% a 85% e por isso ainda é A
    v = _vendas([("2026-01-10", "D1", "a", 1, 70), ("2026-01-10", "D2", "b", 1, 15), ("2026-01-10", "D3", "c", 1, 15)])
    assert curva_abc(v)["classe"].tolist() == ["A", "A", "B"]


def test_abc_ignora_vendas_fora_da_janela():
    v = _vendas([("2026-01-10", "D1", "a", 1, 10), ("2024-06-01", "D2", "velho", 1, 999)])
    abc = curva_abc(v, dias=365)
    assert abc["sku"].tolist() == ["a"]


# ------------------------------------------------------------------ capital parado
def _base_parado(historico_inicio="2025-01-01"):
    linhas = [(historico_inicio, "H0", "A", 1, 10),   # só para dar tamanho ao histórico
              ("2026-01-31", "H1", "A", 1, 10),       # A vendeu no último dia
              ("2025-07-15", "H2", "B", 1, 10),       # 200 dias antes do fim
              ("2025-07-15", "H3", "D", 1, 10),
              ("2025-07-15", "H4", "E", 1, 10)]
    return _vendas(linhas)


def test_capital_parado_regras():
    assert (FIM - pd.Timestamp("2025-07-15")).days == 200
    est = _estoque([("A", 5, 10, 20, None, False),
                    ("B", 10, 5, 9, None, False),     # parado: 10 x 5 = 50
                    ("C", 4, 10, 18, None, False),    # nunca vendeu, histórico longo: 4 x 10 = 40
                    ("D", 3, 7, 12, None, True),      # sempre mantenho: fora dos alertas (21)
                    ("E", 0, 9, 15, None, False)])    # sem estoque: nada parado
    itens, r = capital_parado(est, _base_parado(), dias=180)
    assert sorted(itens["sku"]) == ["B", "C"]
    assert r["total"] == pytest.approx(90)
    assert r["itens"] == 2
    assert r["valor_sempre_mantenho"] == pytest.approx(21)
    assert r["historico_suficiente"] is True
    assert itens.set_index("sku").at["C", "nunca_vendeu"]
    assert r["pct_do_estoque"] == pytest.approx(90 / (50 + 50 + 40 + 21 + 0))


def test_capital_parado_historico_curto_nao_acusa_item_que_nunca_vendeu():
    v = _vendas([("2026-01-01", "H1", "A", 1, 10), ("2026-01-31", "H2", "A", 1, 10)])  # 31 dias de histórico
    est = _estoque([("A", 5, 10, 20, None, False), ("C", 4, 10, 18, None, False)])
    itens, r = capital_parado(est, v, dias=180)
    assert itens.empty and r["total"] == 0
    assert r["historico_suficiente"] is False


# ------------------------------------------------------------------ ruptura
def _vendas_diarias(sku, preco, dias=90, qtd=1):
    return [((FIM - pd.Timedelta(days=i)).strftime("%Y-%m-%d"), f"{sku}{i}", sku, qtd, preco) for i in range(dias)]


def test_ruptura_conta_conhecida():
    # X: 1 un/dia, estoque 5, prazo 7 + segurança 3 -> cobertura 5 < 10 -> em risco
    # sugestão = ceil(1 x (7+30) - 5) = 32 ; dias sem estoque = 7 - 5 = 2 ; venda em risco = 2 x 1 x 150
    # Z: classe A mas com 200 un. -> sem risco. Y: classe C -> fora.
    v = _vendas(_vendas_diarias("X", 100) + _vendas_diarias("Z", 50) + [("2026-01-20", "Y1", "Y", 1, 1)])
    est = _estoque([("X", 5, 60, 150, 7, False), ("Z", 200, 20, 80, 7, False), ("Y", 1, 1, 2, 7, False)])
    abc = curva_abc(v)
    assert abc.set_index("sku")["classe"].to_dict() == {"X": "A", "Z": "A", "Y": "C"}

    itens, r = risco_ruptura(est, v, abc, janela=90, lead=7, seguranca=3, alvo=30)
    assert itens["sku"].tolist() == ["X"]
    x = itens.iloc[0]
    assert x["venda_diaria"] == pytest.approx(1.0)
    assert x["cobertura_dias"] == pytest.approx(5.0)
    assert x["qtd_sugerida"] == 32
    assert x["valor_compra"] == pytest.approx(32 * 60)
    assert x["venda_em_risco"] == pytest.approx(2 * 1 * 150)
    assert r["itens"] == 1 and r["compra_sugerida"] == pytest.approx(1920)


def test_ruptura_usa_prazo_padrao_quando_fornecedor_nao_informa():
    v = _vendas(_vendas_diarias("X", 100))
    est = _estoque([("X", 9, 60, 150, None, False)])  # cobertura 9 < 7+3 com o prazo padrão
    itens, _ = risco_ruptura(est, v, curva_abc(v), janela=90, lead=7, seguranca=3, alvo=30)
    assert itens["sku"].tolist() == ["X"]


def test_ruptura_item_sem_venda_nao_e_risco():
    v = _vendas(_vendas_diarias("X", 100))
    est = _estoque([("X", 100, 60, 150, 7, False), ("N", 0, 5, 9, 7, False)])  # N nunca vendeu
    itens, _ = risco_ruptura(est, v, curva_abc(v))
    assert itens.empty


# ------------------------------------------------------------------ giro
def test_giro_por_categoria():
    v = _vendas(_vendas_diarias("X", 100, dias=365))
    v["custo_unitario"] = 40.0
    est = _estoque([("X", 10, 40, 100, 7, False)])  # estoque a custo 400; CMV anual 365 x 40 = 14.600
    g = giro_por(est, v, por="categoria", dias=365)
    assert g.at[0, "giro_anual"] == pytest.approx(14600 / 400)
    assert g.at[0, "cobertura_dias"] == pytest.approx(10.0)


# ------------------------------------------------------------------ dia x hora
def test_dia_hora():
    assert pd.Timestamp("2026-11-09").day_of_week == 0 and pd.Timestamp("2026-11-14").day_of_week == 5
    v = _vendas([("2026-11-09 09:15", "D1", "a", 1, 60), ("2026-11-09 09:20", "D1", "b", 1, 40),  # mesma venda: 100
                 ("2026-11-09 09:45", "D2", "a", 1, 50),
                 ("2026-11-14 11:00", "D3", "a", 2, 100)])
    r = dia_hora(v)
    assert r["horas"] == [9, 10, 11]
    assert r["faturamento"].at[0, 9] == 150 and r["vendas"].at[0, 9] == 2
    assert r["faturamento"].at[5, 11] == 200 and r["vendas"].at[5, 11] == 1
    assert r["top"][0] == {"dia": "Sáb", "hora": 11, "valor": 200.0}


def test_vendedores():
    v = _vendas([("2026-01-10", "D1", "a", 1, 100, "Ana"), ("2026-01-10", "D1", "b", 1, 50, "Ana"),
                 ("2026-01-11", "D2", "a", 1, 30, "Ana"), ("2026-01-11", "D3", "a", 1, 200, "Beto")])
    g = desempenho_vendedores(v).set_index("vendedor")
    assert g.at["Ana", "vendas"] == 2 and g.at["Ana", "faturamento"] == 180
    assert g.at["Ana", "ticket_medio"] == 90 and g.at["Ana", "itens_por_venda"] == 1.5
    assert desempenho_vendedores(v.drop(columns="vendedor")) is None


# ------------------------------------------------------------------ orçamentos e vendas perdidas
def test_conversao_orcamentos():
    o = pd.DataFrame([("O1", "a", 1, 100, True, "Ana"), ("O1", "b", 1, 50, True, "Ana"),
                      ("O2", "a", 1, 100, False, "Ana"), ("O3", "a", 2, 100, False, "Beto"),
                      ("O4", "c", 1, 30, False, "Beto")],
                     columns=["documento", "sku", "quantidade", "preco_unitario", "convertido", "vendedor"])
    est = _estoque([("a", 1, 1, 1, 7, False), ("c", 1, 1, 1, 7, False)])
    r = conversao_orcamentos(o, est)
    assert r["orcamentos"] == 4 and r["convertidos"] == 1 and r["taxa"] == pytest.approx(0.25)
    assert r["valor_nao_convertido"] == pytest.approx(100 + 200 + 30)
    por_v = r["por_vendedor"].set_index("vendedor")
    assert por_v.at["Ana", "taxa"] == pytest.approx(0.5) and por_v.at["Beto", "taxa"] == 0
    top = r["top_nao_convertidos"].set_index("sku")
    assert top.at["a", "vezes"] == 2 and top.at["c", "vezes"] == 1


def test_vendas_perdidas_e_devolucoes():
    est = _estoque([("a", 1, 1, 100, 7, False), ("b", 1, 1, 40, 7, False)])
    est.loc[est["sku"] == "b", "fornecedor"] = "Outro"
    p = pd.DataFrame([("a", "Item a", 2, "sem_estoque"), ("a", "Item a", 1, "sem_estoque"),
                      ("b", "Item b", 1, "devolucao_incompatibilidade"), (None, "Peça sem cadastro", 1, "preco")],
                     columns=["sku", "descricao", "quantidade", "motivo"])
    r = vendas_perdidas(p, est, {"sem_estoque": "Sem estoque"})
    assert r["ocorrencias"] == 4
    assert r["valor_estimado"] == pytest.approx(3 * 100 + 40)  # a peça sem cadastro vale 0, não quebra
    assert r["devolucoes"] == 1
    assert r["devolucoes_por_fornecedor"].iloc[0]["fornecedor"] == "Outro"
    assert r["ranking"].iloc[0]["sku"] == "a" and r["ranking"].iloc[0]["ocorrencias"] == 2
    assert vendas_perdidas(None, est, {}) is None
