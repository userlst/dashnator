"""Lista de compra em Excel: uma aba por fornecedor e uma aba de resumo."""
import io
import re

import pandas as pd

COLUNAS = {"sku": "Código", "descricao": "Item", "classe": "Classe", "quantidade_atual": "Estoque",
           "venda_diaria": "Venda por dia", "cobertura_dias": "Dura (dias)", "qtd_sugerida": "Comprar (un.)",
           "custo_unitario": "Custo unitário (R$)", "valor_compra": "Custo da compra (R$)"}


def _nome_da_aba(nome: str, usados: set[str]) -> str:
    base = re.sub(r"[\[\]:*?/\\]", " ", str(nome)).strip()[:31] or "Sem fornecedor"
    aba, n = base, 2
    while aba in usados or aba == "Resumo":
        sufixo = f" ({n})"
        aba, n = base[: 31 - len(sufixo)] + sufixo, n + 1
    usados.add(aba)
    return aba


def lista_de_compra(ruptura_itens: pd.DataFrame) -> bytes:
    """Itens em risco com quantidade sugerida > 0, agrupados por fornecedor. Devolve o .xlsx em bytes."""
    itens = ruptura_itens[ruptura_itens["qtd_sugerida"] > 0].copy()
    if "fornecedor" not in itens:
        itens["fornecedor"] = "Sem fornecedor"
    itens["fornecedor"] = itens["fornecedor"].fillna("Sem fornecedor")
    for c, casas in (("venda_diaria", 2), ("cobertura_dias", 1), ("custo_unitario", 2), ("valor_compra", 2)):
        itens[c] = itens[c].round(casas)

    saida = io.BytesIO()
    usados: set[str] = set()
    resumo = []
    with pd.ExcelWriter(saida, engine="openpyxl") as planilha:
        pd.DataFrame().to_excel(planilha, sheet_name="Resumo")  # reserva a primeira posição
        for fornecedor, grupo in itens.groupby("fornecedor", sort=True):
            aba = _nome_da_aba(fornecedor, usados)
            tabela = grupo.sort_values("valor_compra", ascending=False)[list(COLUNAS)].rename(columns=COLUNAS)
            tabela.to_excel(planilha, sheet_name=aba, index=False)
            resumo.append({"Fornecedor": aba, "Itens": len(tabela), "Comprar (un.)": int(tabela["Comprar (un.)"].sum()),
                           "Custo da compra (R$)": round(float(tabela["Custo da compra (R$)"].sum()), 2)})
            folha = planilha.sheets[aba]
            folha.column_dimensions["B"].width = 46
            for letra in "ACDEFGHI":
                folha.column_dimensions[letra].width = 18
        colunas_resumo = ["Fornecedor", "Itens", "Comprar (un.)", "Custo da compra (R$)"]
        pd.DataFrame(resumo, columns=colunas_resumo).to_excel(planilha, sheet_name="Resumo", index=False)
        for letra, largura in zip("ABCD", (34, 10, 16, 24)):
            planilha.sheets["Resumo"].column_dimensions[letra].width = largura
    return saida.getvalue()
