"""Importador: planilha da loja (Excel/CSV/DataFrame) -> tabelas canônicas, com avisos de qualidade.

Privacidade: só as colunas do mapeamento entram. Colunas com cara de dado pessoal (CPF, CNPJ, telefone,
e-mail, nome de cliente) são descartadas e o aviso diz qual coluna foi. Nenhuma linha vai para log.
"""
import io
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from dashnator.core.periodo import dias_de_historico, fim_data, inicio_data


class ErroDeImportacao(Exception):
    """Problema no arquivo que o dono consegue corrigir (mensagem em português)."""


# Tabelas canônicas: colunas fixas que as análises usam.
TABELAS = {
    "vendas": {"obrigatorias": ["data_hora", "documento", "sku", "descricao", "quantidade", "preco_unitario"],
               "opcionais": ["custo_unitario", "categoria", "marca", "vendedor"]},
    "estoque": {"obrigatorias": ["sku", "descricao", "quantidade_atual", "custo_unitario", "preco_venda"],
                "opcionais": ["categoria", "marca", "fornecedor", "lead_time_dias", "sempre_mantenho"]},
    "orcamentos": {"obrigatorias": ["documento", "sku", "quantidade", "preco_unitario", "convertido"],
                   "opcionais": ["data_hora", "vendedor"]},
    "perdidas": {"obrigatorias": ["descricao", "quantidade", "motivo"],
                 "opcionais": ["sku", "data_hora", "fornecedor"]},
}
ROTULOS = {"vendas": "vendas", "estoque": "estoque", "orcamentos": "orçamentos", "perdidas": "vendas perdidas"}
TEXTO = {"documento", "sku", "descricao", "categoria", "marca", "vendedor", "fornecedor", "motivo"}
DINHEIRO = {"preco_unitario", "custo_unitario", "preco_venda"}
NUMERO = {"quantidade", "quantidade_atual", "lead_time_dias"}
SEM_INFORMACAO = "Não informado"

_VERDADEIRO = {"sim", "s", "1", "true", "verdadeiro", "v", "x", "yes", "y", "aprovado", "convertido",
               "fechado", "vendido", "faturado", "ganho"}


# ------------------------------------------------------------------ conversores
def para_numero(s: pd.Series, dinheiro: bool = False) -> pd.Series:
    """Números escritos à brasileira ('1.234,56', 'R$ 10,50') ou com ponto decimal ('12.5').

    Em coluna de dinheiro, '1.234' é R$ 1.234 (ponto de milhar), não 1,234.
    """
    def um(v):
        if v is None or (isinstance(v, float) and np.isnan(v)) or v is pd.NA:
            return np.nan
        if isinstance(v, (int, float, np.integer, np.floating)) and not isinstance(v, bool):
            return float(v)
        t = str(v).replace("R$", "").replace(" ", "").replace(" ", "").strip()
        if not t:
            return np.nan
        if "," in t:
            t = t.replace(".", "").replace(",", ".")
        elif t.count(".") > 1:
            t = t.replace(".", "")
        elif dinheiro and re.fullmatch(r"-?\d{1,3}\.\d{3}", t):
            t = t.replace(".", "")
        try:
            return float(t)
        except ValueError:
            return np.nan

    return s.map(um).astype(float)


_FORMATOS_BR = ("%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M", "%d/%m/%Y")


def para_data(s: pd.Series) -> pd.Series:
    """Datas em ISO ('2026-01-05 10:30') ou no formato brasileiro ('05/01/2026 14:20'), misturadas."""
    if pd.api.types.is_datetime64_any_dtype(s):
        return s

    def um(v):
        if v is None or v is pd.NA or (isinstance(v, float) and np.isnan(v)):
            return pd.NaT
        if isinstance(v, (pd.Timestamp, np.datetime64)) or hasattr(v, "isoformat"):
            return pd.Timestamp(v)
        t = str(v).strip()
        if re.match(r"\d{4}-\d{1,2}-\d{1,2}", t):
            return pd.to_datetime(t, errors="coerce")
        if re.match(r"\d{1,2}/\d{1,2}/\d{4}", t):
            for formato in _FORMATOS_BR:
                d = pd.to_datetime(t, format=formato, errors="coerce")
                if not pd.isna(d):
                    return d
        return pd.NaT

    return pd.to_datetime(s.map(um))


def para_booleano(s: pd.Series) -> pd.Series:
    """'Sim', 'S', '1', 'Aprovado'... -> True; o resto (inclusive vazio) -> False."""
    if pd.api.types.is_bool_dtype(s):
        return s.fillna(False).astype(bool)

    def um(v):
        if v is None or v is pd.NA or (isinstance(v, float) and np.isnan(v)):
            return False
        if isinstance(v, (bool, np.bool_)):
            return bool(v)
        if isinstance(v, (int, float, np.integer, np.floating)):
            return v == 1
        return _sem_acento(str(v)).strip().lower() in _VERDADEIRO

    return s.map(um).astype(bool)


def _sem_acento(t: str) -> str:
    return unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode()


# ------------------------------------------------------------------ privacidade
_NOMES_PESSOAIS = ("cpf", "cnpj", "telefone", "celular", "fone", "whatsapp", "email", "e-mail", "cliente",
                   "razao social", "endereco", "nascimento")
_PADROES_PESSOAIS = {
    "CPF": re.compile(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b"),
    "CNPJ": re.compile(r"\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b"),
    "e-mail": re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+"),
    "telefone": re.compile(r"\(?\b\d{2}\)?\s?9?\d{4}-\d{4}\b"),
}


def _dado_pessoal(nome_coluna: str, valores: pd.Series) -> str | None:
    """Diz que tipo de dado pessoal a coluna parece ter (ou None). Olha o nome e uma amostra."""
    nome = _sem_acento(str(nome_coluna)).lower()
    for trecho in _NOMES_PESSOAIS:
        if trecho in nome:
            return "nome ou contato de cliente" if trecho in ("cliente", "razao social", "endereco") else trecho.upper() \
                if trecho in ("cpf", "cnpj") else trecho
    amostra = valores.dropna().astype(str).head(50)
    for tipo, padrao in _PADROES_PESSOAIS.items():
        if amostra.map(lambda t: bool(padrao.search(t))).any():
            return tipo
    return None


# ------------------------------------------------------------------ leitura
def _ler(origem) -> pd.DataFrame:
    if isinstance(origem, pd.DataFrame):
        return origem.copy()
    nome = str(getattr(origem, "name", origem)).lower()
    if isinstance(origem, (str, Path)):
        conteudo = Path(origem).read_bytes()
    else:  # arquivo enviado pelo painel
        conteudo = origem.getvalue() if hasattr(origem, "getvalue") else origem.read()
    try:
        if nome.endswith((".xlsx", ".xlsm", ".xls")):
            return pd.read_excel(io.BytesIO(conteudo))
        try:
            texto = conteudo.decode("utf-8-sig")
        except UnicodeDecodeError:
            texto = conteudo.decode("latin-1")
        primeira = texto.split("\n", 1)[0]
        separador = max((";", ",", "\t"), key=primeira.count)
        return pd.read_csv(io.StringIO(texto), sep=separador, dtype=str, keep_default_na=False)
    except ErroDeImportacao:
        raise
    except Exception as e:
        raise ErroDeImportacao(f"Não consegui ler o arquivo ({type(e).__name__}). "
                               "Envie em Excel (.xlsx) ou CSV.") from e


def _plural(n: int, um: str, varios: str) -> str:
    return f"{n} {um if n == 1 else varios}"


# ------------------------------------------------------------------ importar uma tabela
def importar(tipo: str, origem, mapeamento: dict | None = None) -> tuple[pd.DataFrame, list[str]]:
    """Converte a planilha em tabela canônica. Devolve (tabela, avisos).

    mapeamento: {coluna canônica: nome da coluna no arquivo}. Sem mapeamento, o arquivo já precisa
    usar os nomes canônicos.
    """
    if tipo not in TABELAS:
        raise ErroDeImportacao(f"Tipo de arquivo desconhecido: {tipo}")
    bruto = _ler(origem)
    bruto.columns = [str(c).strip() for c in bruto.columns]
    esquema = TABELAS[tipo]
    canonicas = esquema["obrigatorias"] + esquema["opcionais"]
    rotulo = ROTULOS[tipo]
    avisos: list[str] = []

    mapa = {c: c for c in canonicas if c in bruto.columns}
    if mapeamento:
        inexistentes = [col for canon, col in mapeamento.items() if col not in bruto.columns]
        if inexistentes:
            raise ErroDeImportacao(f"Arquivo de {rotulo}: as colunas {', '.join(map(repr, inexistentes))} do "
                                   f"mapeamento não existem no arquivo. Colunas do arquivo: {', '.join(bruto.columns)}.")
        desconhecidas = [c for c in mapeamento if c not in canonicas]
        if desconhecidas:
            raise ErroDeImportacao(f"Arquivo de {rotulo}: o mapeamento usa campos que não existem "
                                   f"({', '.join(desconhecidas)}). Campos aceitos: {', '.join(canonicas)}.")
        mapa.update(mapeamento)
    faltando = [c for c in esquema["obrigatorias"] if c not in mapa]
    if faltando:
        raise ErroDeImportacao(f"Arquivo de {rotulo}: faltam as colunas {', '.join(faltando)}. "
                               f"Colunas do arquivo: {', '.join(bruto.columns)}. Informe o mapeamento.")

    # privacidade: o que não está no mapeamento fica de fora; avisa quando parece dado pessoal
    usadas = set(mapa.values())
    for coluna in bruto.columns:
        if coluna in usadas:
            continue
        pessoal = _dado_pessoal(coluna, bruto[coluna])
        if pessoal:
            avisos.append(f"A coluna '{coluna}' do arquivo de {rotulo} parece ter dados pessoais ({pessoal}) "
                          "e foi descartada.")

    df = pd.DataFrame({canon: bruto[col].to_numpy() for canon, col in mapa.items()})
    for c in df.columns:
        if c in TEXTO:
            df[c] = df[c].astype("string").str.strip()
            df.loc[df[c] == "", c] = pd.NA
        elif c in DINHEIRO or c in NUMERO:
            df[c] = para_numero(df[c], dinheiro=c in DINHEIRO)
        elif c == "data_hora":
            df[c] = para_data(df[c])
        elif c in ("convertido", "sempre_mantenho"):
            df[c] = para_booleano(df[c])

    limpar = {"vendas": _limpar_vendas, "estoque": _limpar_estoque,
              "orcamentos": _limpar_orcamentos, "perdidas": _limpar_perdidas}[tipo]
    df = limpar(df, avisos).reset_index(drop=True)
    return df, avisos


def _descartar(df: pd.DataFrame, mascara: pd.Series, avisos: list[str], motivo: str) -> pd.DataFrame:
    n = int(mascara.sum())
    if n:
        avisos.append(f"{_plural(n, 'linha', 'linhas')} {motivo} e ficou fora do cálculo." if n == 1
                      else f"{n} linhas {motivo} e ficaram fora do cálculo.")
    return df[~mascara]


def _limpar_vendas(df: pd.DataFrame, avisos: list[str]) -> pd.DataFrame:
    df = _descartar(df, df["sku"].isna(), avisos, "de vendas sem código do item")
    df = _descartar(df, df["data_hora"].isna(), avisos, "de vendas com data que não consegui ler")
    df = _descartar(df, df["data_hora"] > pd.Timestamp.now() + pd.Timedelta(days=1), avisos,
                    "de vendas com data no futuro")
    df = _descartar(df, ~(df["quantidade"] > 0), avisos, "de vendas com quantidade menor ou igual a zero")
    df = _descartar(df, ~(df["preco_unitario"] > 0), avisos, "de vendas com preço zero ou vazio")
    df["descricao"] = df["descricao"].fillna(df["sku"])
    df["documento"] = df["documento"].fillna("sem número")
    return df


def _limpar_estoque(df: pd.DataFrame, avisos: list[str]) -> pd.DataFrame:
    df = df[df["sku"].notna()]
    repetidos = int(df["sku"].duplicated().sum())
    if repetidos:
        avisos.append(f"Códigos repetidos no arquivo de estoque ({repetidos}): ficou a primeira linha de cada um.")
        df = df.drop_duplicates("sku", keep="first")
    df = df.copy()
    negativos = int((df["quantidade_atual"] < 0).sum())
    if negativos:
        avisos.append(f"{_plural(negativos, 'item', 'itens')} com estoque negativo no cadastro: "
                      "tratei como zero.")
    df["quantidade_atual"] = df["quantidade_atual"].fillna(0).clip(lower=0)
    sem_custo = int((df["custo_unitario"].isna() | (df["custo_unitario"] <= 0)).sum())
    if sem_custo:
        avisos.append(f"{_plural(sem_custo, 'item', 'itens')} sem custo no cadastro: o dinheiro parado "
                      "e a margem desses itens ficam subestimados.")
    df["custo_unitario"] = df["custo_unitario"].fillna(0).clip(lower=0)
    df["preco_venda"] = df["preco_venda"].fillna(0).clip(lower=0)
    df["descricao"] = df["descricao"].fillna(df["sku"])
    for c in ("categoria", "marca", "fornecedor"):
        if c not in df:
            df[c] = pd.Series(SEM_INFORMACAO, index=df.index, dtype="string")
        df[c] = df[c].fillna(SEM_INFORMACAO)
    if "lead_time_dias" not in df:
        df["lead_time_dias"] = np.nan
    df.loc[~(df["lead_time_dias"] > 0), "lead_time_dias"] = np.nan
    if "sempre_mantenho" not in df:
        df["sempre_mantenho"] = False
    return df


def _limpar_orcamentos(df: pd.DataFrame, avisos: list[str]) -> pd.DataFrame:
    df = _descartar(df, df["sku"].isna() | df["documento"].isna(), avisos,
                    "de orçamentos sem código do item ou sem número")
    df = _descartar(df, ~(df["quantidade"] > 0) | ~(df["preco_unitario"] > 0), avisos,
                    "de orçamentos com quantidade ou preço zero")
    return df


def _limpar_perdidas(df: pd.DataFrame, avisos: list[str]) -> pd.DataFrame:
    if "sku" not in df:
        df["sku"] = pd.Series(pd.NA, index=df.index, dtype="string")
    df["quantidade"] = df["quantidade"].fillna(1)
    df = _descartar(df, ~(df["quantidade"] > 0), avisos, "de vendas perdidas com quantidade zero")
    df = df.copy()
    df["motivo"] = df["motivo"].fillna("outro")
    df["descricao"] = df["descricao"].fillna(df["sku"]).fillna("Item não identificado")
    return df


# ------------------------------------------------------------------ conjunto de dados da loja
@dataclass
class Dataset:
    vendas: pd.DataFrame
    estoque: pd.DataFrame
    orcamentos: pd.DataFrame | None
    perdidas: pd.DataFrame | None
    nome_loja: str
    fim: pd.Timestamp            # data de referência: a última venda
    inicio: pd.Timestamp
    dias_historico: int
    custo_nas_vendas: bool
    tem_hora: bool
    avisos: list[str] = field(default_factory=list)


def carregar_dataset(vendas, estoque, orcamentos=None, perdidas=None, mapeamentos: dict | None = None,
                     nome_loja: str = "Loja", min_historico_dias: int = 90) -> Dataset:
    """Importa os arquivos da loja e junta os avisos de qualidade de dados."""
    mapeamentos = mapeamentos or {}
    avisos: list[str] = []
    v, a = importar("vendas", vendas, mapeamentos.get("vendas"))
    avisos += a
    e, a = importar("estoque", estoque, mapeamentos.get("estoque"))
    avisos += a
    o = p = None
    if orcamentos is not None:
        o, a = importar("orcamentos", orcamentos, mapeamentos.get("orcamentos"))
        avisos += a
    if perdidas is not None:
        p, a = importar("perdidas", perdidas, mapeamentos.get("perdidas"))
        avisos += a
    if v.empty:
        raise ErroDeImportacao("O arquivo de vendas não tem nenhuma linha válida.")
    if e.empty:
        raise ErroDeImportacao("O arquivo de estoque não tem nenhum item válido.")

    dias = dias_de_historico(v)
    if dias < min_historico_dias:
        avisos.append(f"Histórico de vendas de apenas {_plural(dias, 'dia', 'dias')}: a curva ABC e os dias de "
                      f"estoque ficam pouco confiáveis com menos de {min_historico_dias} dias.")
    custo_nas_vendas = "custo_unitario" in v and v["custo_unitario"].notna().any()
    if not custo_nas_vendas:
        avisos.append("As vendas não trazem custo: a margem usa o custo atual do cadastro de estoque.")
        v["custo_unitario"] = v["sku"].map(e.set_index("sku")["custo_unitario"].where(lambda c: c > 0))
    tem_hora = bool((v["data_hora"] != v["data_hora"].dt.normalize()).any())
    if not tem_hora:
        avisos.append("As vendas vieram sem hora: o quadro de dia e hora fica desligado.")

    vendidos, cadastrados = set(v["sku"].dropna()), set(e["sku"])
    fora_do_estoque = len(vendidos - cadastrados)
    if fora_do_estoque:
        avisos.append(f"{fora_do_estoque} SKUs vendidos não estão no arquivo de estoque "
                      "(ficam fora do dinheiro parado e do risco de faltar).")
    if o is not None and "descricao" not in o:
        o["descricao"] = o["sku"].map(e.set_index("sku")["descricao"]).fillna(o["sku"])

    return Dataset(vendas=v, estoque=e, orcamentos=o, perdidas=p, nome_loja=nome_loja, fim=fim_data(v),
                   inicio=inicio_data(v), dias_historico=dias, custo_nas_vendas=bool(custo_nas_vendas),
                   tem_hora=tem_hora, avisos=avisos)
