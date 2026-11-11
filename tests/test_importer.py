import pandas as pd
import pytest

from dashnator.core.importer import ErroDeImportacao, carregar_dataset, importar, para_booleano, para_data, para_numero


def test_numeros_ptbr():
    s = pd.Series(["1.234,56", "R$ 10,50", "7", "12.5", "abc", None])
    r = para_numero(s).tolist()
    assert r[:4] == [1234.56, 10.5, 7.0, 12.5] and pd.isna(r[4]) and pd.isna(r[5])


def test_dinheiro_com_ponto_de_milhar_nao_vira_centavos():
    # "1.234" numa coluna de preço é R$ 1.234, não 1,23
    assert para_numero(pd.Series(["1.234", "12.500", "89.9"]), dinheiro=True).tolist() == [1234.0, 12500.0, 89.9]
    assert para_numero(pd.Series(["1.234.567"])).tolist() == [1234567.0]


def test_datas_misturadas():
    s = pd.Series(["2026-01-05 10:30:00", "05/01/2026 14:20", "31/12/2025", "lixo"])
    r = para_data(s)
    assert r.iloc[0] == pd.Timestamp("2026-01-05 10:30")
    assert r.iloc[1] == pd.Timestamp("2026-01-05 14:20")
    assert r.iloc[2] == pd.Timestamp("2025-12-31")
    assert pd.isna(r.iloc[3])


def test_booleanos():
    assert para_booleano(pd.Series(["Sim", "não", "S", "1", "Aprovado", ""])).tolist() == [True, False, True, True, True, False]


def _vendas_brutas():
    return pd.DataFrame({
        "Data": ["05/01/2026 10:00", "06/01/2026 11:30", "07/01/2026 09:10", "08/01/2026 09:10"],
        "Pedido": ["1", "2", "3", "4"],
        "Código": ["A", "B", "A", "C"],
        "Produto": ["Pastilha", "Filtro", "Pastilha", "Vela"],
        "Qtd": ["2", "1,0", "0", "1"],              # quantidade 0 é descartada
        "Preço": ["1.234,50", "R$ 30,00", "50", "10"],
        "Nome do Cliente": ["João", "Maria", "Ana", "Pedro"],
        "CPF": ["111.222.333-44", "", "", ""],
    })


MAP_VENDAS = {"data_hora": "Data", "documento": "Pedido", "sku": "Código", "descricao": "Produto",
              "quantidade": "Qtd", "preco_unitario": "Preço"}


def test_mapeamento_privacidade_e_limpeza():
    df, avisos = importar("vendas", _vendas_brutas(), MAP_VENDAS)
    assert len(df) == 3
    assert df["preco_unitario"].iloc[0] == 1234.5 and df["quantidade"].iloc[1] == 1.0
    assert not {"Nome do Cliente", "CPF"} & set(df.columns)
    assert any("Nome do Cliente" in a for a in avisos) and any("CPF" in a for a in avisos)
    assert any("menor ou igual a zero" in a for a in avisos)


def test_coluna_do_mapeamento_inexistente_e_coluna_obrigatoria_faltando():
    with pytest.raises(ErroDeImportacao, match="não existem"):
        importar("vendas", _vendas_brutas(), {**MAP_VENDAS, "sku": "Inexistente"})
    with pytest.raises(ErroDeImportacao, match="faltam"):
        importar("vendas", _vendas_brutas())  # sem mapeamento, nomes não são os canônicos


def test_estoque_duplicado_negativo_e_sem_custo():
    bruto = pd.DataFrame({"sku": ["A", "A", "B", "C"], "descricao": ["a", "a", "b", "c"],
                          "quantidade_atual": ["5", "9", "-2", "3"], "custo_unitario": ["10,00", "10,00", "", "4,00"],
                          "preco_venda": ["20,00", "20,00", "15,00", "8,00"]})
    df, avisos = importar("estoque", bruto)
    assert df["sku"].tolist() == ["A", "B", "C"]
    assert df.set_index("sku").at["B", "quantidade_atual"] == 0
    assert df.set_index("sku").at["B", "custo_unitario"] == 0
    assert not df["sempre_mantenho"].any()
    assert any("repetidos" in a for a in avisos) and any("negativo" in a for a in avisos) and any("sem custo" in a for a in avisos)


def test_csv_com_ponto_e_virgula_e_latin1(tmp_path):
    arq = tmp_path / "vendas.csv"
    arq.write_bytes("Data;Pedido;Código;Produto;Qtd;Preço\n05/01/2026 10:00;1;A;Pastilha de freio;2;1.234,50\n".encode("latin-1"))
    df, _ = importar("vendas", arq, MAP_VENDAS)
    assert df["descricao"].iloc[0] == "Pastilha de freio" and df["preco_unitario"].iloc[0] == 1234.5


def test_dataset_avisos_de_qualidade():
    est = pd.DataFrame({"sku": ["A"], "descricao": ["a"], "quantidade_atual": [1], "custo_unitario": [1], "preco_venda": [2]})
    ds = carregar_dataset(_vendas_brutas(), est, mapeamentos={"vendas": MAP_VENDAS})
    texto = " ".join(ds.avisos)
    assert "Histórico de vendas" in texto           # só 3 dias
    assert "não trazem custo" in texto
    assert "SKUs vendidos não estão no arquivo de estoque" in texto
