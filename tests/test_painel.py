"""Peças do painel web (Streamlit): login, lista de compra, texto de compartilhar e o app de ponta a ponta."""
import io
from urllib.parse import parse_qs, urlparse

import pandas as pd
import pytest

from dashnator.ai.verify import numeros_nao_verificados
from dashnator.cli import exportar_csv
from dashnator.config import carregar_nicho
from dashnator.core.importer import carregar_dataset
from dashnator.demo.generate import gerar_dados
from dashnator.diagnostico import diagnosticar
from dashnator.report.excel import lista_de_compra
from dashnator.web.acesso import confere, credenciais
from dashnator.web.compartilhar import link_whatsapp, texto_para_compartilhar


@pytest.fixture(scope="module")
def diag():
    dados = gerar_dados(n_skus=200, docs_por_dia=15.0)
    ds = carregar_dataset(dados["vendas"], dados["estoque"], dados["orcamentos"], dados["perdidas"],
                          nome_loja="Loja Teste")
    return diagnosticar(ds, carregar_nicho("autopecas"))


# ------------------------------------------------------------------ login
def test_login_padrao_da_apresentacao():
    assert credenciais({}) == ("teste", "teste")
    assert confere("teste", "teste", {})
    assert not confere("teste", "errada", {})
    assert not confere("", "", {})


def test_login_configuravel_sem_mexer_no_codigo():
    segredos = {"DASHNATOR_USUARIO": "dono", "DASHNATOR_SENHA": "s3nh4-forte"}
    assert confere("dono", "s3nh4-forte", segredos)
    assert not confere("teste", "teste", segredos)
    assert confere(" Dono ", "s3nh4-forte", segredos)       # usuário ignora espaços e maiúsculas
    assert not confere("dono", "S3NH4-FORTE", segredos)     # senha não


# ------------------------------------------------------------------ lista de compra em Excel
def test_lista_de_compra_uma_aba_por_fornecedor_e_totais_batem(diag):
    itens = diag.res["ruptura_itens"]
    assert len(itens) > 0
    abas = pd.read_excel(io.BytesIO(lista_de_compra(itens)), sheet_name=None)
    assert "Resumo" in abas
    fornecedores = set(itens.loc[itens["qtd_sugerida"] > 0, "fornecedor"])
    assert fornecedores <= set(abas)
    linhas = pd.concat([abas[f] for f in fornecedores])
    assert linhas["Comprar (un.)"].sum() == itens["qtd_sugerida"].sum()
    assert linhas["Custo da compra (R$)"].sum() == pytest.approx(diag.res["ruptura"]["compra_sugerida"], abs=0.01 * len(linhas))
    assert abas["Resumo"]["Custo da compra (R$)"].sum() == pytest.approx(linhas["Custo da compra (R$)"].sum())


def test_lista_de_compra_vazia_nao_quebra(diag):
    abas = pd.read_excel(io.BytesIO(lista_de_compra(diag.res["ruptura_itens"].head(0))), sheet_name=None)
    assert list(abas) == ["Resumo"]


# ------------------------------------------------------------------ compartilhar
def test_texto_de_compartilhar_so_tem_numeros_do_payload(diag):
    texto = texto_para_compartilhar(diag.insights, diag.ds.nome_loja, diag.payload["periodo"]["dados_ate"])
    assert "Loja Teste" in texto and "O que fazer" in texto
    assert numeros_nao_verificados(texto, diag.payload) == []


def test_link_whatsapp_sem_api(diag):
    texto = texto_para_compartilhar(diag.insights, diag.ds.nome_loja, diag.payload["periodo"]["dados_ate"])
    url = urlparse(link_whatsapp(texto))
    assert url.netloc == "wa.me" and url.path == "/"
    assert parse_qs(url.query)["text"][0] == texto


# ------------------------------------------------------------------ CSV de loja dá o mesmo resultado
def test_csv_exportado_da_o_mesmo_diagnostico(diag, tmp_path):
    dados = gerar_dados(n_skus=200, docs_por_dia=15.0)
    exportar_csv(dados, tmp_path)
    ds = carregar_dataset(tmp_path / "vendas.csv", tmp_path / "estoque.csv", tmp_path / "orcamentos.csv",
                          tmp_path / "perdidas.csv", nome_loja="Loja Teste")
    do_csv = diagnosticar(ds, carregar_nicho("autopecas"))
    assert do_csv.payload["kpis"] == diag.payload["kpis"]


# ------------------------------------------------------------------ o app, sem navegador
def _app():
    from streamlit.testing.v1 import AppTest
    from pathlib import Path
    return AppTest.from_file(str(Path(__file__).resolve().parent.parent / "streamlit_app.py"), default_timeout=60)


def test_app_abre_na_tela_de_login():
    at = _app().run()
    assert not at.exception
    assert len(at.text_input) == 2 and not at.metric          # nada do painel antes de entrar
    assert any("Dashnator" in t.value for t in at.title)


def test_app_recusa_senha_errada():
    at = _app().run()
    at.text_input[0].set_value("teste")
    at.text_input[1].set_value("errada")
    at.button[0].click().run()
    assert not at.exception and at.error and not at.metric


def test_app_entra_e_mostra_o_painel_da_demo():
    at = _app().run()
    at.text_input[0].set_value("teste")
    at.text_input[1].set_value("teste")
    at.button[0].click().run()
    assert not at.exception
    rotulos = [m.label for m in at.metric]
    assert "Faturamento" in rotulos and "Dinheiro parado" in rotulos
    assert any("Dados de demonstração" in w.value for w in at.warning)
    # sair volta para o login
    next(b for b in at.button if b.label == "Sair").click().run()
    assert not at.exception and not at.metric and len(at.text_input) == 2
