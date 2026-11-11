"""Dashnator no Streamlit: login, dados (demonstração ou arquivos da loja) e as telas do painel.

Rodar:  streamlit run streamlit_app.py
Este arquivo só monta a tela. Todo número vem de dashnator.diagnostico (o mesmo caminho do relatório
HTML) e toda formatação de número passa por dashnator.ai.fmt. Nenhuma chamada de IA acontece aqui.
"""
import hashlib
import json
import time

import altair as alt
import pandas as pd
import streamlit as st

from dashnator.ai import fmt
from dashnator.analyses.dia_hora import DIAS
from dashnator.cli import para_csv
from dashnator.config import carregar_nicho
from dashnator.core.importer import TABELAS, ErroDeImportacao, carregar_dataset
from dashnator.demo.generate import NOME_LOJA_DEMO, gerar_dados
from dashnator.diagnostico import Diagnostico, diagnosticar
from dashnator.report.excel import lista_de_compra
from dashnator.report.html import render
from dashnator.web.acesso import MAX_TENTATIVAS, confere
from dashnator.web.compartilhar import link_whatsapp, texto_para_compartilhar

AZUL, VERDE, AMBAR, CINZA = "#1f5eff", "#17784a", "#a76a0a", "#5f6877"
NICHO = "autopecas"
AJUSTES = {  # parâmetro do nicho: (rótulo na tela, mínimo, máximo)
    "encalhe_dias": ("Dias sem venda para contar como parado", 30, 720),
    "lead_time_dias": ("Prazo de entrega do fornecedor (dias)", 1, 90),
    "margem_seguranca_dias": ("Folga de segurança (dias)", 0, 30),
    "cobertura_alvo_dias": ("Dias de venda que a compra deve cobrir", 7, 180),
    "janela_venda_dias": ("Dias usados na média de venda", 30, 365),
}

st.set_page_config(page_title="Dashnator", page_icon="📊", layout="wide")


def md(texto: str) -> str:
    """Texto seguro para o markdown do Streamlit (o cifrão de 'R$' abriria uma fórmula)."""
    return str(texto).replace("$", "\\$")


def segredos() -> dict:
    try:
        return dict(st.secrets)
    except Exception:  # sem arquivo de segredos: vale o login padrão da apresentação
        return {}


# =============================================================================== login
def tela_de_login() -> None:
    _, meio, _ = st.columns([1, 1.3, 1])
    with meio:
        st.title("📊 Dashnator")
        st.markdown("**Onde está o dinheiro parado, o que vai faltar e o que fazer hoje.**")
        st.caption("Diagnóstico de estoque e vendas para a sua loja, com números calculados por regras fixas.")
        with st.form("login"):
            usuario = st.text_input("Usuário")
            senha = st.text_input("Senha", type="password")
            entrar = st.form_submit_button("Entrar", type="primary", use_container_width=True)
        if entrar:
            tentativas = st.session_state.get("tentativas", 0)
            if tentativas >= MAX_TENTATIVAS:
                st.error("Muitas tentativas. Feche esta aba, abra de novo e tente outra vez.")
            elif confere(usuario, senha, segredos()):
                st.session_state.clear()
                st.session_state["logado"] = True
                st.rerun()
            else:
                st.session_state["tentativas"] = tentativas + 1
                time.sleep(0.6)
                st.error("Usuário ou senha incorretos.")
        st.caption("Versão de apresentação.")


# =============================================================================== dados
@st.cache_data(show_spinner="Montando a loja de demonstração…")
def diagnostico_da_demo(ajustes: tuple) -> Diagnostico:
    dados = gerar_dados()
    ds = carregar_dataset(dados["vendas"], dados["estoque"], dados["orcamentos"], dados["perdidas"],
                          nome_loja=NOME_LOJA_DEMO)
    return diagnosticar(ds, carregar_nicho(NICHO, dict(ajustes)))


@st.cache_data(show_spinner=False)
def arquivos_de_exemplo() -> dict[str, bytes]:
    dados = gerar_dados(n_skus=200, docs_por_dia=12.0)
    return {nome: para_csv(df) for nome, df in dados.items()}


def diagnostico_da_loja(ajustes: tuple) -> Diagnostico | None:
    """Lê os arquivos enviados. Fica só na memória desta sessão: nada é gravado em disco."""
    barra = st.sidebar
    nome = barra.text_input("Nome da loja", value="Minha loja")
    vendas = barra.file_uploader("Vendas (obrigatório)", type=["csv", "xlsx"], key="arq_vendas")
    estoque = barra.file_uploader("Estoque (obrigatório)", type=["csv", "xlsx"], key="arq_estoque")
    orcamentos = barra.file_uploader("Orçamentos (opcional)", type=["csv", "xlsx"], key="arq_orcamentos")
    perdidas = barra.file_uploader("Vendas perdidas (opcional)", type=["csv", "xlsx"], key="arq_perdidas")
    mapa = barra.file_uploader("Mapeamento de colunas (opcional, .json)", type=["json"], key="arq_mapa")
    if vendas is None or estoque is None:
        return None

    marca = hashlib.sha256()
    for arquivo in (vendas, estoque, orcamentos, perdidas, mapa):
        marca.update(arquivo.getvalue() if arquivo is not None else b"-")
    chave = (marca.hexdigest(), nome, ajustes)
    guardado = st.session_state.get("diagnostico_loja")
    if guardado and guardado[0] == chave:
        return guardado[1]
    try:
        mapeamentos = json.loads(mapa.getvalue().decode("utf-8-sig")) if mapa is not None else None
        cfg = carregar_nicho(NICHO, dict(ajustes))
        with st.spinner("Lendo os arquivos e calculando…"):
            ds = carregar_dataset(vendas, estoque, orcamentos, perdidas, mapeamentos=mapeamentos,
                                  nome_loja=nome.strip() or "Minha loja",
                                  min_historico_dias=cfg["min_historico_dias"])
            d = diagnosticar(ds, cfg)
    except ErroDeImportacao as e:
        st.error(md(f"Não deu para ler os arquivos. {e}"))
        return None
    except json.JSONDecodeError:
        st.error("O arquivo de mapeamento não é um JSON válido.")
        return None
    st.session_state["diagnostico_loja"] = (chave, d)
    return d


def como_preparar_os_arquivos() -> None:
    st.subheader("Envie os arquivos da loja")
    st.markdown("Na barra ao lado, envie o arquivo de **vendas** e o de **estoque** (Excel ou CSV), "
                "exportados do sistema da loja. Orçamentos e vendas perdidas são opcionais.")
    st.info("Colunas com CPF, CNPJ, telefone, e-mail ou nome de cliente são descartadas na leitura. "
            "Os arquivos ficam só na memória enquanto esta aba estiver aberta: nada é gravado.")
    with st.expander("Quais colunas cada arquivo precisa ter", expanded=True):
        nomes = {"vendas": "Vendas", "estoque": "Estoque", "orcamentos": "Orçamentos",
                 "perdidas": "Vendas perdidas"}
        for tipo, esquema in TABELAS.items():
            st.markdown(f"**{nomes[tipo]}** — obrigatórias: `{'`, `'.join(esquema['obrigatorias'])}`  \n"
                        f"opcionais: `{'`, `'.join(esquema['opcionais'])}`")
        st.caption("Se as colunas do seu sistema têm outros nomes, envie também um mapeamento em JSON, "
                   'no formato {"vendas": {"data_hora": "Data", "sku": "Código", ...}, "estoque": {...}}.')
    st.markdown("**Arquivos de exemplo** (dados fictícios, já no formato certo):")
    colunas = st.columns(4)
    for coluna, (nome, conteudo) in zip(colunas, arquivos_de_exemplo().items()):
        coluna.download_button(f"{nome}.csv", conteudo, file_name=f"{nome}.csv", mime="text/csv",
                               use_container_width=True)


# =============================================================================== peças de tela
def tabela(df: pd.DataFrame, colunas: dict, altura: int | str = "auto") -> None:
    """colunas: {coluna: (título, formatador ou None)}. Números formatados por fmt (pt-BR)."""
    visao = pd.DataFrame({titulo: (df[c].map(f) if f else df[c].astype("string").fillna(""))
                          for c, (titulo, f) in colunas.items() if c in df})
    st.dataframe(visao, hide_index=True, use_container_width=True, height=altura)


def barras(pares: list[tuple[str, float]], formatar=fmt.reais, cor: str = AZUL) -> None:
    if not pares:
        return
    df = pd.DataFrame(pares, columns=["rotulo", "valor"])
    df["texto"] = df["valor"].map(formatar)
    base = alt.Chart(df).encode(y=alt.Y("rotulo:N", sort=None, title=None, axis=alt.Axis(labelLimit=220)),
                                x=alt.X("valor:Q", axis=None),
                                tooltip=[alt.Tooltip("rotulo:N", title="Item"), alt.Tooltip("texto:N", title="Valor")])
    grafico = base.mark_bar(color=cor, cornerRadiusEnd=3) + base.mark_text(align="left", dx=5).encode(text="texto:N")
    st.altair_chart(grafico.properties(height=max(90, 34 * len(df))), use_container_width=True)


def grafico_abc(abc: pd.DataFrame) -> None:
    n = len(abc)
    if not n:
        return
    passo = max(1, n // 300)
    df = abc.iloc[::passo].assign(pct_itens=lambda d: (d.index + 1) / n)
    df = pd.concat([pd.DataFrame({"pct_itens": [0.0], "pct_acumulado": [0.0], "classe": ["A"]}),
                    df[["pct_itens", "pct_acumulado", "classe"]]])
    grafico = alt.Chart(df).mark_area(line={"color": AZUL}, color=AZUL, opacity=0.15).encode(
        x=alt.X("pct_itens:Q", title="% dos itens (do mais ao menos vendido)", axis=alt.Axis(format=".0%")),
        y=alt.Y("pct_acumulado:Q", title="% do faturamento acumulado", axis=alt.Axis(format=".0%")))
    st.altair_chart(grafico.properties(height=300), use_container_width=True)


def mapa_dia_hora(dh: dict) -> None:
    linhas = [{"dia": DIAS[d], "hora": f"{h}h", "valor": float(dh["faturamento"].at[d, h]),
               "faturamento": fmt.reais(dh["faturamento"].at[d, h]),
               "vendas": fmt.inteiro(dh["vendas"].at[d, h]),
               "mil": fmt.inteiro(dh["faturamento"].at[d, h] / 1000) if dh["faturamento"].at[d, h] else ""}
              for d in range(7) for h in dh["horas"] if dh["faturamento"].loc[d].sum() > 0]
    df = pd.DataFrame(linhas)
    base = alt.Chart(df).encode(
        x=alt.X("hora:O", sort=[f"{h}h" for h in dh["horas"]], title=None, axis=alt.Axis(labelAngle=0, orient="top")),
        y=alt.Y("dia:O", sort=DIAS, title=None),
        tooltip=[alt.Tooltip("dia:N", title="Dia"), alt.Tooltip("hora:N", title="Hora"),
                 alt.Tooltip("faturamento:N", title="Faturamento"), alt.Tooltip("vendas:N", title="Vendas")])
    limite = df["valor"].max() * 0.5
    grafico = (base.mark_rect().encode(color=alt.Color("valor:Q", scale=alt.Scale(scheme="blues"), legend=None))
               + base.mark_text(fontSize=11).encode(
                   text="mil:N", color=alt.condition(alt.datum.valor > limite, alt.value("white"), alt.value("#14181f"))))
    st.altair_chart(grafico.properties(height=44 * df["dia"].nunique() + 40), use_container_width=True)
    st.caption("Valores em R\\$ mil faturados em cada janela (soma do período).")


# =============================================================================== telas
def visao_geral(d: Diagnostico, demo: bool) -> None:
    k, parado, ruptura = d.res["kpis"], d.res["parado"], d.res["ruptura"]
    perdidas, orc = d.res["perdidas"], d.res["orcamentos"]
    if demo:
        st.warning("**Dados de demonstração.** Lojas, produtos, marcas, vendedores e números são fictícios.")
    if d.ds.avisos:
        with st.expander(f"Atenção com os dados ({len(d.ds.avisos)})"):
            for aviso in d.ds.avisos:
                st.markdown(f"- {md(aviso)}")

    cartoes = [("Faturamento", fmt.reais(k["faturamento"]), f"últimos {k['dias']} dias"),
               ("Ticket médio", fmt.reais(k["ticket_medio"]), f"{fmt.inteiro(k['vendas'])} vendas")]
    if k["margem"] is not None:
        cartoes.append(("Margem bruta", fmt.pct(k["margem"] * 100), "sobre o faturamento"))
    cartoes.append(("Dinheiro parado", fmt.reais(parado["total"]),
                    f"{fmt.pct(parado['pct_do_estoque'] * 100)} do estoque · {fmt.inteiro(parado['itens'])} itens"))
    cartoes.append(("Itens em risco de faltar", fmt.inteiro(ruptura["itens"]),
                    f"venda em risco {fmt.reais(ruptura['venda_em_risco'])}"))
    if perdidas:
        cartoes.append(("Vendas perdidas", fmt.reais(perdidas["valor_estimado"]),
                        f"{fmt.inteiro(perdidas['ocorrencias'])} registros"))
    if orc:
        cartoes.append(("Conversão de orçamentos", fmt.pct(orc["taxa"] * 100),
                        f"{fmt.inteiro(orc['orcamentos'])} orçamentos"))
    for inicio in range(0, len(cartoes), 4):
        for coluna, (titulo, valor, sub) in zip(st.columns(4), cartoes[inicio:inicio + 4]):
            with coluna.container(border=True):
                st.metric(titulo, valor)
                st.caption(md(sub))

    st.subheader("O que fazer agora")
    st.caption("Resumo e prioridades, ordenados pelo impacto em reais.")
    ins = d.insights
    st.info(md(ins["resumo"]))
    for a in ins["alertas"]:
        with st.container(border=True):
            st.markdown(f"**{a['prioridade']}. {md(a['titulo'])}** · impacto de {md(fmt.reais(a['impacto_reais']))}")
            st.markdown(md(a["por_que"]))
            st.success(md(f"**O que fazer:** {a['acao']}"))
    if ins["oportunidades"]:
        st.markdown("**Oportunidades**")
        for o in ins["oportunidades"]:
            st.markdown(f"- {md(o['texto'])} {md(o['acao'])}")

    with st.expander("Compartilhar o resumo"):
        texto = texto_para_compartilhar(ins, d.ds.nome_loja, d.payload["periodo"]["dados_ate"])
        st.caption("Copie o texto pelo botão no canto do quadro, ou abra o WhatsApp já com ele escrito. "
                   "Quem envia é você: o Dashnator não manda mensagem por conta própria.")
        st.code(texto, language=None, wrap_lines=True)
        st.link_button("Enviar pelo WhatsApp", link_whatsapp(texto))


def tela_estoque(d: Diagnostico) -> None:
    parado, ruptura = d.res["parado"], d.res["ruptura"]
    itens_parados, itens_risco = d.res["parado_itens"], d.res["ruptura_itens"]

    st.subheader("Dinheiro parado em estoque")
    st.caption(f"Itens com estoque e sem venda há {parado['dias']} dias ou mais, valorizados a custo.")
    if itens_parados.empty:
        st.info("Nenhum item parado." if parado["historico_suficiente"] else
                f"O histórico tem menos de {parado['dias']} dias: ainda não dá para dizer o que está parado.")
    else:
        a, b, c = st.columns(3)
        a.metric("Dinheiro parado", fmt.reais(parado["total"]))
        b.metric("Parte do estoque", fmt.pct(parado["pct_do_estoque"] * 100))
        c.metric("Itens parados", fmt.inteiro(parado["itens"]))
        esquerda, direita = st.columns(2)
        with esquerda:
            st.markdown("**Por categoria**")
            barras([(r.categoria, r.valor_parado) for r in parado["por_categoria"].head(8).itertuples()])
        with direita:
            st.markdown("**Por fornecedor**")
            barras([(r.fornecedor, r.valor_parado) for r in parado["por_fornecedor"].head(8).itertuples()], cor=AMBAR)
        st.markdown("**Itens parados** (do maior valor para o menor)")
        visao = itens_parados.assign(sem_venda=[
            "sem venda no período" if nunca else fmt.inteiro(dias)
            for nunca, dias in zip(itens_parados["nunca_vendeu"], itens_parados["dias_sem_venda"])])
        tabela(visao, {"descricao": ("Item", None), "categoria": ("Categoria", None), "fornecedor": ("Fornecedor", None),
                       "quantidade_atual": ("Qtd", fmt.inteiro), "sem_venda": ("Sem venda há (dias)", None),
                       "valor_parado": ("Valor parado", fmt.reais)}, altura=380)
        if parado["valor_sempre_mantenho"]:
            st.caption(md(f"Fora da conta: {fmt.reais(parado['valor_sempre_mantenho'])} em itens marcados como "
                          "'sempre mantenho'."))

    st.divider()
    st.subheader("Itens que vão faltar")
    st.caption(f"Classes A e B cujo estoque dura menos que o prazo do fornecedor mais "
               f"{fmt.inteiro(ruptura['seguranca'])} dias. Compra sugerida: cobre {fmt.inteiro(ruptura['alvo'])} "
               "dias de venda além do prazo.")
    if itens_risco.empty:
        st.info("Nenhum item importante em risco de faltar.")
        return
    a, b, c = st.columns(3)
    a.metric("Itens em risco", fmt.inteiro(ruptura["itens"]))
    b.metric("Venda em risco", fmt.reais(ruptura["venda_em_risco"]))
    c.metric("Compra sugerida", fmt.reais(ruptura["compra_sugerida"]))
    tabela(itens_risco, {"descricao": ("Item", None), "classe": ("Classe", None), "fornecedor": ("Fornecedor", None),
                         "quantidade_atual": ("Estoque", fmt.inteiro), "cobertura_dias": ("Dura (dias)", fmt.dias),
                         "venda_diaria": ("Venda/dia", lambda v: fmt.numero(v, 2)),
                         "qtd_sugerida": ("Comprar (un.)", fmt.inteiro), "valor_compra": ("Custo da compra", fmt.reais),
                         "venda_em_risco": ("Venda em risco", fmt.reais)}, altura=380)
    st.download_button("Baixar a lista de compra em Excel (uma aba por fornecedor)", lista_de_compra(itens_risco),
                       file_name="lista_de_compra.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", type="primary")
    st.caption("A venda por dia inclui os dias em que o item já estava em falta; nesses itens, a necessidade "
               "real pode ser maior.")


def tela_abc(d: Diagnostico) -> None:
    abc, resumo = d.res["abc"], d.res["resumo_abc"]
    st.subheader("Curva ABC")
    st.caption("Poucos itens sustentam a maior parte do faturamento. Os da classe A não podem faltar.")
    esquerda, direita = st.columns([3, 2])
    with esquerda:
        grafico_abc(abc)
    with direita:
        tabela(resumo.reset_index(), {"classe": ("Classe", None), "itens": ("Itens", fmt.inteiro),
                                      "pct_itens": ("% dos itens", lambda v: fmt.pct(v * 100)),
                                      "faturamento": ("Faturamento", fmt.reais),
                                      "pct_valor": ("% do faturamento", lambda v: fmt.pct(v * 100))})
        cortes = d.cfg["corte_abc"]
        st.caption(f"A: até {fmt.inteiro(cortes[0] * 100)}% do faturamento acumulado. "
                   f"B: até {fmt.inteiro(cortes[1] * 100)}%. C: o restante.")
    classes = st.multiselect("Classes na lista", ["A", "B", "C"], default=["A"])
    estoque = d.ds.estoque.set_index("sku")["quantidade_atual"]
    visao = abc[abc["classe"].isin(classes)].assign(estoque=lambda t: t["sku"].map(estoque))
    tabela(visao, {"descricao": ("Item", None), "classe": ("Classe", None), "quantidade": ("Qtd vendida", fmt.inteiro),
                   "faturamento": ("Faturamento", fmt.reais), "pct": ("% do faturamento", lambda v: fmt.pct(v * 100, 2)),
                   "estoque": ("Estoque hoje", fmt.inteiro)}, altura=420)


def tela_vendas(d: Diagnostico) -> None:
    st.subheader("Quando a loja vende mais")
    if d.res["dia_hora"]:
        mapa_dia_hora(d.res["dia_hora"])
    else:
        st.info("As vendas vieram sem hora: não dá para montar o quadro de dia e hora.")

    vendedores, orc = d.res["vendedores"], d.res["orcamentos"]
    st.subheader("Equipe")
    if vendedores is None:
        st.info("O arquivo de vendas não tem a coluna de vendedor.")
    else:
        visao = vendedores.copy()
        colunas = {"vendedor": ("Vendedor", None), "vendas": ("Vendas", fmt.inteiro),
                   "faturamento": ("Faturamento", fmt.reais), "ticket_medio": ("Ticket médio", fmt.reais),
                   "itens_por_venda": ("Itens por venda", lambda v: fmt.numero(v, 1))}
        if orc and orc["por_vendedor"] is not None:
            visao["conversao"] = visao["vendedor"].map(orc["por_vendedor"].set_index("vendedor")["taxa"])
            colunas["conversao"] = ("Conversão de orçamentos", lambda v: fmt.pct(v * 100))
        tabela(visao, colunas)

    st.subheader("Giro e dias de estoque")
    por = st.radio("Agrupar por", ["categoria", "fornecedor", "marca"], horizontal=True,
                   format_func=str.capitalize)
    st.caption("Giro anual = venda a custo anualizada ÷ valor do estoque de hoje (não há histórico de estoque).")
    tabela(d.res["giro"][por], {por: (por.capitalize(), None), "estoque_custo": ("Estoque a custo", fmt.reais),
                                "cmv_anual": ("Venda a custo/ano", fmt.reais),
                                "giro_anual": ("Giro/ano", lambda v: fmt.numero(v, 1)),
                                "cobertura_dias": ("Estoque dura (dias)", fmt.inteiro)})


def tela_perdidas(d: Diagnostico) -> None:
    perdidas, orc = d.res["perdidas"], d.res["orcamentos"]
    st.subheader("Vendas perdidas e devoluções")
    st.caption("Registros do balcão: o cliente pediu e não saiu vendido (ou voltou por incompatibilidade).")
    if not perdidas:
        st.info("Nenhum arquivo de vendas perdidas foi enviado. Ele é opcional: colunas descricao, quantidade "
                "e motivo (e, se tiver, sku).")
    else:
        a, b, c = st.columns(3)
        a.metric("Registros", fmt.inteiro(perdidas["ocorrencias"]))
        b.metric("Valor estimado", fmt.reais(perdidas["valor_estimado"]))
        c.metric("Devoluções por incompatibilidade", fmt.inteiro(perdidas["devolucoes"]))
        esquerda, direita = st.columns(2)
        with esquerda:
            st.markdown("**Motivos**")
            barras([(r.rotulo, r.casos) for r in perdidas["por_motivo"].itertuples()],
                   formatar=lambda v: f"{fmt.inteiro(v)} {'caso' if v == 1 else 'casos'}", cor=AMBAR)
            if not perdidas["devolucoes_por_fornecedor"].empty:
                st.markdown("**Devoluções por incompatibilidade, por fornecedor**")
                tabela(perdidas["devolucoes_por_fornecedor"], {"fornecedor": ("Fornecedor", None),
                                                               "casos": ("Casos", fmt.inteiro)})
        with direita:
            st.markdown("**Itens que mais escaparam**")
            tabela(perdidas["ranking"], {"descricao": ("Item", None), "ocorrencias": ("Vezes", fmt.inteiro),
                                         "quantidade": ("Qtd", fmt.inteiro), "valor": ("Valor estimado", fmt.reais)})

    st.divider()
    st.subheader("Orçamentos que não viraram venda")
    if not orc:
        st.info("Nenhum arquivo de orçamentos foi enviado. Ele é opcional.")
        return
    a, b, c = st.columns(3)
    a.metric("Orçamentos", fmt.inteiro(orc["orcamentos"]))
    b.metric("Viraram venda", fmt.pct(orc["taxa"] * 100))
    c.metric("Valor não convertido", fmt.reais(orc["valor_nao_convertido"]))
    esquerda, direita = st.columns(2)
    with esquerda:
        if orc["por_vendedor"] is not None:
            st.markdown("**Conversão por vendedor**")
            barras([(r.vendedor, r.taxa * 100) for r in orc["por_vendedor"].itertuples()], formatar=fmt.pct, cor=VERDE)
    with direita:
        st.markdown("**Itens mais orçados e não vendidos**")
        tabela(orc["top_nao_convertidos"], {"descricao": ("Item", None), "vezes": ("Orçamentos", fmt.inteiro),
                                            "valor": ("Valor", fmt.reais)})


def tela_relatorio(d: Diagnostico, demo: bool) -> None:
    st.subheader("Relatório para imprimir ou enviar")
    st.markdown("O mesmo conteúdo do painel num arquivo só, que abre em qualquer celular ou computador, "
                "funciona sem internet e imprime em PDF (abra o arquivo e use o botão **Imprimir / salvar PDF**).")
    nome = "demo" if demo else "relatorio"
    st.download_button("Baixar o relatório (HTML)", render(d.ds, d.cfg, d.res, d.insights, demo=demo),
                       file_name=f"dashnator_{nome}.html", mime="text/html", type="primary")
    st.divider()
    cfg = d.cfg
    st.markdown("**Como os números são calculados**")
    st.markdown(
        "Tudo é calculado por regras fixas, não por estimativa de IA.\n"
        f"- **Venda por dia:** quantidade vendida nos últimos {cfg['janela_venda_dias']} dias ÷ {cfg['janela_venda_dias']}.\n"
        "- **Dias de estoque:** estoque ÷ venda por dia.\n"
        f"- **Risco de faltar:** item classe A ou B com dias de estoque abaixo do prazo do fornecedor "
        f"({cfg['lead_time_dias']} dias, se o cadastro não disser outro) mais {cfg['margem_seguranca_dias']} dias de folga.\n"
        f"- **Compra sugerida:** o que falta para cobrir o prazo mais {cfg['cobertura_alvo_dias']} dias de venda.\n"
        f"- **Dinheiro parado:** item com estoque e sem venda há {cfg['encalhe_dias']} dias ou mais, a custo. "
        "Itens marcados como 'sempre mantenho' ficam fora.\n"
        f"- **Curva ABC:** A até {fmt.inteiro(cfg['corte_abc'][0] * 100)}% do faturamento acumulado, "
        f"B até {fmt.inteiro(cfg['corte_abc'][1] * 100)}%.")
    st.caption("Limitações desta versão: o giro usa o estoque de hoje; a venda por dia inclui dias em que o item "
               "estava em falta; sazonalidade ainda não entra na conta.")


# =============================================================================== app
def painel() -> None:
    barra = st.sidebar
    barra.title("📊 Dashnator")
    fonte = barra.radio("Dados", ["Demonstração", "Arquivos da minha loja"],
                        help="A demonstração usa uma loja fictícia de autopeças.")
    padrao = carregar_nicho(NICHO)
    with barra.expander("Ajustes da análise"):
        valores = {chave: st.number_input(rotulo, min_value=minimo, max_value=maximo, value=int(padrao[chave]), step=1)
                   for chave, (rotulo, minimo, maximo) in AJUSTES.items()}
        st.caption("Mudou um ajuste, os números são recalculados na hora.")
    ajustes = tuple(sorted(valores.items()))

    demo = fonte == "Demonstração"
    d = diagnostico_da_demo(ajustes) if demo else diagnostico_da_loja(ajustes)
    barra.divider()
    if barra.button("Sair", use_container_width=True):
        st.session_state.clear()
        st.rerun()

    if d is None:
        como_preparar_os_arquivos()
        return
    st.title(d.ds.nome_loja)
    st.caption(f"Dados até {d.payload['periodo']['dados_ate']} · {fmt.inteiro(d.ds.dias_historico)} dias de histórico "
               f"· pacote {d.cfg.get('rotulo', '')}")
    abas = st.tabs(["Visão geral", "Estoque", "Curva ABC", "Vendas", "Perdidas e orçamentos", "Relatório"])
    with abas[0]:
        visao_geral(d, demo)
    with abas[1]:
        tela_estoque(d)
    with abas[2]:
        tela_abc(d)
    with abas[3]:
        tela_vendas(d)
    with abas[4]:
        tela_perdidas(d)
    with abas[5]:
        tela_relatorio(d, demo)


if st.session_state.get("logado"):
    painel()
else:
    tela_de_login()
