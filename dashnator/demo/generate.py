"""Gerador de dados fictícios de uma loja de autopeças (semente e data de referência fixas).

100% inventado: marcas, códigos, fornecedores e vendedores não existem. O resultado é reproduzível.
Segue docs/BRIEF.md seção 9: Pareto nas vendas, ~10% de itens encalhados, ~5% de itens classe A com
pouco estoque, mais vendas em dias úteis e dois picos de horário.
"""
import numpy as np
import pandas as pd

FIM_DEMO = "2026-11-10"
NOME_LOJA_DEMO = "Auto Peças Exemplo"

# categoria: (peso de venda, faixa de preço, produtos)
CATALOGO = {
    "Filtros": (1.5, (18, 90), ["Filtro de óleo", "Filtro de ar", "Filtro de combustível", "Filtro de cabine"]),
    "Lubrificantes": (1.5, (25, 80), ["Óleo 5W30", "Óleo 10W40", "Óleo 15W40", "Óleo de câmbio", "Fluido de freio"]),
    "Freios": (1.3, (45, 320), ["Pastilha de freio dianteira", "Pastilha de freio traseira", "Disco de freio",
                                "Cilindro mestre", "Lona de freio"]),
    "Suspensão": (1.1, (60, 520), ["Amortecedor dianteiro", "Amortecedor traseiro", "Pivô de suspensão",
                                   "Bieleta", "Bucha de bandeja"]),
    "Motor": (1.0, (30, 480), ["Vela de ignição", "Correia dentada", "Kit de distribuição", "Junta do cabeçote",
                               "Bomba de óleo"]),
    "Transmissão": (0.9, (55, 620), ["Kit de embreagem", "Cabo de embreagem", "Semieixo", "Junta homocinética"]),
    "Elétrica": (0.8, (12, 780), ["Bateria 60Ah", "Alternador", "Motor de partida", "Bobina de ignição",
                                  "Lâmpada de farol", "Lâmpada de placa"]),
    "Arrefecimento": (0.7, (28, 430), ["Radiador", "Bomba d'água", "Mangueira superior", "Aditivo de radiador",
                                       "Válvula termostática"]),
    "Acessórios": (0.6, (15, 160), ["Palheta do limpador", "Trava elétrica", "Tapete de borracha", "Calota"]),
    "Direção": (0.35, (70, 900), ["Caixa de direção", "Bomba de direção", "Terminal axial", "Terminal de direção"]),
    "Ar-condicionado": (0.25, (90, 1900), ["Compressor", "Condensador", "Válvula de expansão", "Filtro secador"]),
}
MARCAS = [f"Marca {c}" for c in "ABCDEFGH"]
FORNECEDORES = [f"Distribuidora {i}" for i in range(1, 9)]
VENDEDORES = [f"Vendedor {c}" for c in "ABCDE"]
PESO_VENDEDOR = [0.28, 0.24, 0.20, 0.16, 0.12]
CONVERSAO_VENDEDOR = [0.72, 0.69, 0.62, 0.50, 0.47]
# peso de cada dia da semana (segunda = 0) e de cada hora
PESO_DIA = [1.05, 1.0, 1.0, 1.0, 1.15, 0.55, 0.0]
HORAS_SEMANA = (list(range(8, 18)), [1.40, 1.20, 0.90, 0.40, 0.22, 0.22, 0.45, 0.90, 1.00, 1.15])
HORAS_SABADO = ([8, 9, 10, 11], [1.2, 1.3, 1.0, 0.5])
MOTIVOS = (["sem_estoque", "preco", "devolucao_incompatibilidade", "sem_aplicacao", "outro"],
           [0.45, 0.25, 0.15, 0.10, 0.05])


def _catalogo(rng: np.random.Generator, n_skus: int) -> pd.DataFrame:
    categorias = list(CATALOGO)
    partes = rng.choice(len(categorias), size=n_skus, p=_normalizar([1.0] * len(categorias)))
    linhas = []
    for i, c in enumerate(partes):
        categoria = categorias[c]
        peso_cat, (pmin, pmax), produtos = CATALOGO[categoria]
        produto = produtos[rng.integers(len(produtos))]
        marca = MARCAS[rng.integers(len(MARCAS))]
        preco = float(np.exp(rng.uniform(np.log(pmin), np.log(pmax))))
        if "Lâmpada" in produto or "Palheta" in produto:
            preco = float(rng.uniform(4, 35))
        linhas.append({
            "sku": f"P{i + 1:05d}",
            "descricao": f"{produto} - {marca} - Aplic. V{rng.integers(1, 61):02d}",
            "categoria": categoria, "marca": marca,
            "fornecedor": FORNECEDORES[rng.integers(len(FORNECEDORES))],
            "preco_venda": round(preco, 2),
            "custo_unitario": round(preco * rng.uniform(0.52, 0.68), 2),
            "peso_cat": peso_cat,
        })
    cat = pd.DataFrame(linhas)
    # Pareto: poucos itens concentram a venda
    ordem = rng.permutation(n_skus)
    popularidade = np.empty(n_skus)
    popularidade[ordem] = (np.arange(n_skus) + 1.0) ** -1.05
    cat["peso"] = popularidade * cat["peso_cat"] / (cat["preco_venda"] / 60) ** 0.12
    return cat.drop(columns="peso_cat")


def _normalizar(pesos) -> np.ndarray:
    p = np.asarray(pesos, dtype=float)
    return p / p.sum()


def gerar_dados(n_skus: int = 800, docs_por_dia: float = 36.0, semente: int = 7, fim: str = FIM_DEMO) -> dict:
    """Devolve {'vendas', 'estoque', 'orcamentos', 'perdidas'} já nas colunas canônicas."""
    rng = np.random.default_rng(semente)
    fim_ts = pd.Timestamp(fim)
    dias = pd.date_range(fim_ts - pd.Timedelta(days=364), fim_ts, freq="D")
    cat = _catalogo(rng, n_skus)

    # ~10% encalhados: param de vender entre 180 e 365 dias atrás (alguns nem venderam no período)
    caros = cat["categoria"].isin(["Ar-condicionado", "Elétrica", "Direção", "Arrefecimento", "Transmissão", "Motor"])
    chance = np.where(caros, 2.0, 0.6) * (cat["preco_venda"].to_numpy() ** 0.3)
    encalhados = rng.choice(n_skus, size=max(3, round(n_skus * 0.10)), replace=False, p=_normalizar(chance))
    parou_em = pd.Series(pd.NaT, index=range(n_skus), dtype="datetime64[ns]")
    parou_em.loc[encalhados] = [fim_ts - pd.Timedelta(days=int(d)) for d in rng.integers(181, 480, size=len(encalhados))]

    # ---------------------------------------------------------------- vendas
    dia_semana = dias.day_of_week.to_numpy()
    docs_no_dia = rng.poisson(docs_por_dia * np.array(PESO_DIA)[dia_semana])
    n_docs = int(docs_no_dia.sum())
    doc_dia = np.repeat(np.arange(len(dias)), docs_no_dia)
    sabado = dia_semana[doc_dia] == 5
    hora = np.where(sabado, rng.choice(HORAS_SABADO[0], size=n_docs, p=_normalizar(HORAS_SABADO[1])),
                    rng.choice(HORAS_SEMANA[0], size=n_docs, p=_normalizar(HORAS_SEMANA[1])))
    momento = (dias[doc_dia] + pd.to_timedelta(hora, unit="h")
               + pd.to_timedelta(rng.integers(0, 60, size=n_docs), unit="m"))
    vendedor = rng.choice(VENDEDORES, size=n_docs, p=PESO_VENDEDOR)
    itens_no_doc = 1 + rng.poisson(0.7, size=n_docs)

    linha_doc = np.repeat(np.arange(n_docs), itens_no_doc)
    n_linhas = len(linha_doc)
    sku_idx = rng.choice(n_skus, size=n_linhas, p=_normalizar(cat["peso"]))
    preco = cat["preco_venda"].to_numpy()[sku_idx]
    quantidade = np.where(preco < 40, rng.choice([1, 2, 3, 4], size=n_linhas, p=[0.55, 0.25, 0.12, 0.08]),
                          rng.choice([1, 2], size=n_linhas, p=[0.9, 0.1]))
    vendas = pd.DataFrame({
        "data_hora": momento[linha_doc],
        "documento": [f"V{d + 1:06d}" for d in linha_doc],
        "sku": cat["sku"].to_numpy()[sku_idx],
        "descricao": cat["descricao"].to_numpy()[sku_idx],
        "quantidade": quantidade.astype(float),
        "preco_unitario": np.round(preco * (1 - rng.choice([0, 0, 0, 0.03, 0.05, 0.08], size=n_linhas)), 2),
        "custo_unitario": cat["custo_unitario"].to_numpy()[sku_idx],
        "categoria": cat["categoria"].to_numpy()[sku_idx],
        "marca": cat["marca"].to_numpy()[sku_idx],
        "vendedor": vendedor[linha_doc],
    })
    # item encalhado não vende depois da data em que parou
    limite = parou_em.to_numpy()[sku_idx]
    vendas = vendas[pd.isna(limite) | (vendas["data_hora"].to_numpy() <= limite)]
    vendas = vendas.sort_values(["data_hora", "documento"], kind="mergesort").reset_index(drop=True)

    # ---------------------------------------------------------------- estoque
    ultimos_90 = vendas[vendas["data_hora"] > fim_ts - pd.Timedelta(days=90)].groupby("sku")["quantidade"].sum()
    venda_dia = cat["sku"].map(ultimos_90).fillna(0.0).to_numpy() / 90
    dias_de_estoque = rng.uniform(25, 85, size=n_skus)
    quantidade_atual = np.ceil(venda_dia * dias_de_estoque) + rng.integers(0, 3, size=n_skus)
    quantidade_atual[encalhados] = rng.integers(2, 9, size=len(encalhados))

    # ~5% dos itens mais vendidos com pouco estoque (para aparecerem como risco de faltar)
    faturamento = (vendas["quantidade"] * vendas["preco_unitario"]).groupby(vendas["sku"]).sum()
    mais_vendidos = cat["sku"].map(faturamento).fillna(0.0).sort_values(ascending=False).index[: max(8, n_skus // 10)]
    em_risco = rng.choice(mais_vendidos.to_numpy(), size=max(2, round(n_skus * 0.025)), replace=False)
    quantidade_atual[em_risco] = np.floor(venda_dia[em_risco] * rng.uniform(0, 7.5, size=len(em_risco)))

    sempre_mantenho = np.zeros(n_skus, dtype=bool)
    sempre_mantenho[rng.choice(encalhados, size=max(1, len(encalhados) // 14), replace=False)] = True
    estoque = pd.DataFrame({
        "sku": cat["sku"], "descricao": cat["descricao"], "quantidade_atual": quantidade_atual,
        "custo_unitario": cat["custo_unitario"], "preco_venda": cat["preco_venda"],
        "categoria": cat["categoria"], "marca": cat["marca"], "fornecedor": cat["fornecedor"],
        "lead_time_dias": np.nan, "sempre_mantenho": sempre_mantenho,
    })

    # ---------------------------------------------------------------- orçamentos (~65% viram venda)
    n_orc = max(20, round(600 * docs_por_dia / 36))
    orc_vendedor = rng.choice(len(VENDEDORES), size=n_orc, p=PESO_VENDEDOR)
    orc_convertido = rng.random(n_orc) < np.array(CONVERSAO_VENDEDOR)[orc_vendedor]
    orc_itens = 1 + rng.poisson(0.6, size=n_orc)
    orc_doc = np.repeat(np.arange(n_orc), orc_itens)
    # alguns itens são muito orçados e pouco fechados (preço ou prazo)
    dificeis = rng.choice(mais_vendidos.to_numpy(), size=min(6, len(mais_vendidos)), replace=False)
    orc_sku = rng.choice(n_skus, size=len(orc_doc), p=_normalizar(cat["peso"]))
    trocar = (~orc_convertido[orc_doc]) & (rng.random(len(orc_doc)) < 0.45)
    orc_sku[trocar] = rng.choice(dificeis, size=int(trocar.sum()),
                                 p=_normalizar([6, 3.5, 2, 1.3, 1, 0.8][: len(dificeis)]))
    orc_dia = rng.integers(0, 120, size=n_orc)
    orcamentos = pd.DataFrame({
        "data_hora": (fim_ts - pd.to_timedelta(orc_dia[orc_doc], unit="D")
                      + pd.to_timedelta(rng.integers(8, 18, size=len(orc_doc)), unit="h")),
        "documento": [f"O{d + 1:05d}" for d in orc_doc],
        "sku": cat["sku"].to_numpy()[orc_sku],
        "quantidade": rng.choice([1.0, 2.0], size=len(orc_doc), p=[0.85, 0.15]),
        "preco_unitario": cat["preco_venda"].to_numpy()[orc_sku],
        "convertido": orc_convertido[orc_doc],
        "vendedor": np.array(VENDEDORES)[orc_vendedor[orc_doc]],
    })

    # ---------------------------------------------------------------- vendas perdidas (~30)
    n_perdidas = max(8, round(36 * docs_por_dia / 36))
    motivo = rng.choice(MOTIVOS[0], size=n_perdidas, p=MOTIVOS[1])
    perd_sku = np.where(motivo == "sem_estoque", rng.choice(em_risco, size=n_perdidas),
                        rng.choice(mais_vendidos.to_numpy(), size=n_perdidas))
    perdidas = pd.DataFrame({
        "data_hora": fim_ts - pd.to_timedelta(rng.integers(0, 60, size=n_perdidas), unit="D")
                     + pd.to_timedelta(rng.integers(8, 18, size=n_perdidas), unit="h"),
        "sku": cat["sku"].to_numpy()[perd_sku],
        "descricao": cat["descricao"].to_numpy()[perd_sku],
        "quantidade": rng.choice([1.0, 2.0], size=n_perdidas, p=[0.7, 0.3]),
        "motivo": motivo,
    })
    return {"vendas": vendas, "estoque": estoque, "orcamentos": orcamentos, "perdidas": perdidas}
