"""Relatório HTML autossuficiente: CSS inline, gráficos em SVG, sem CDN e sem JavaScript
(só o botão de imprimir). Funciona offline, no celular e imprime em PDF.
"""
from html import escape
from pathlib import Path

import pandas as pd

from dashnator.ai import fmt
from dashnator.analyses.dia_hora import DIAS
from dashnator.core.importer import Dataset

_CSS = (Path(__file__).parent / "estilo.css").read_text(encoding="utf-8")
_AZUL = "31,94,255"


def _e(v) -> str:
    return escape("" if v is None or v is pd.NA else str(v))


def _tabela(colunas: list[tuple[str, bool]], linhas: list[list[str]]) -> str:
    """colunas: (título, é número). linhas: células já formatadas e escapadas."""
    cab = "".join(f"<th{' class=\"n\"' if n else ''}>{_e(t)}</th>" for t, n in colunas)
    corpo = "".join("<tr>" + "".join(f"<td{' class=\"n\"' if colunas[i][1] else ''}>{c}</td>"
                                     for i, c in enumerate(l)) + "</tr>" for l in linhas)
    return f'<div class="scroll"><table><tr>{cab}</tr>{corpo}</table></div>'


def _barras(pares: list[tuple[str, float]], formatar=fmt.reais) -> str:
    maior = max((v for _, v in pares), default=0) or 1
    return "".join(f'<div class="barra"><div>{_e(r)}</div><div class="t"><i style="width:{v / maior * 100:.1f}%"></i>'
                   f'</div><div class="v">{formatar(v)}</div></div>' for r, v in pares)


def _kpi(titulo: str, valor: str, sub: str) -> str:
    return (f'<div class="card kpi"><div class="k">{_e(titulo)}</div><div class="v">{valor}</div>'
            f'<div class="s">{_e(sub)}</div></div>')


def _svg_abc(abc: pd.DataFrame) -> str:
    x0, x1, y0, y1 = 44, 616, 240, 10
    partes = ['<svg viewBox="0 0 640 270" width="100%" role="img" aria-label="Curva ABC">']
    for i in range(6):
        y = y0 - (y0 - y1) * i / 5
        partes.append(f'<line x1="{x0}" x2="{x1}" y1="{y:.1f}" y2="{y:.1f}" stroke="#e3e7ee"/>'
                      f'<text x="38" y="{y + 4:.1f}" font-size="11" text-anchor="end" fill="#5b6574">{i * 20}%</text>')
    for i in range(5):
        x = x0 + (x1 - x0) * i / 4
        partes.append(f'<text x="{x:.1f}" y="260" font-size="11" text-anchor="middle" fill="#5b6574">{i * 25}%</text>')
    n = len(abc)
    if n:
        passo = max(1, n // 250)
        pontos = [(0.0, 0.0)] + [((i + 1) / n, float(p)) for i, p in enumerate(abc["pct_acumulado"])
                                 if i % passo == 0 or i == n - 1]
        coords = " ".join(f"{x0 + (x1 - x0) * px:.1f},{y0 - (y0 - y1) * py:.1f}" for px, py in pontos)
        partes.append(f'<polygon points="{x0},{y0} {coords} {x1},{y0}" fill="rgba({_AZUL},0.10)"/>'
                      f'<polyline points="{coords}" fill="none" stroke="rgb({_AZUL})" stroke-width="2"/>')
    partes.append("</svg>")
    return "".join(partes)


def _mapa_dia_hora(dh: dict) -> str:
    fat, vend = dh["faturamento"], dh["vendas"]
    maior = float(fat.to_numpy().max()) or 1.0
    cab = "<tr><th></th>" + "".join(f"<th>{h}h</th>" for h in dh["horas"]) + "</tr>"
    linhas = []
    for d in range(7):
        if fat.loc[d].sum() == 0:
            continue
        celulas = []
        for h in dh["horas"]:
            v, intensidade = float(fat.at[d, h]), float(fat.at[d, h]) / maior
            cor = "#fff" if intensidade > 0.5 else "#14181f"
            celulas.append(f'<td style="background:rgba({_AZUL},{intensidade:.2f});color:{cor}" '
                           f'title="{DIAS[d]} {h}h: {fmt.reais(v)} em {fmt.inteiro(vend.at[d, h])} vendas">'
                           f'{fmt.inteiro(v / 1000) if v else ""}</td>')
        linhas.append(f"<tr><th>{DIAS[d]}</th>{''.join(celulas)}</tr>")
    return f'<div class="scroll"><table class="heat">{cab}{"".join(linhas)}</table></div>'


def render(ds: Dataset, cfg: dict, res: dict, ins: dict, demo: bool = False) -> str:
    k, parado, ruptura = res["kpis"], res["parado"], res["ruptura"]
    perdidas, orc = res["perdidas"], res["orcamentos"]
    p: list[str] = []

    p.append(f'<div class="top"><div><h1>Diagnóstico de estoque e vendas - {_e(ds.nome_loja)}</h1>'
             f'<p class="sub">Dados até {ds.fim.strftime("%d/%m/%Y")} · {fmt.inteiro(ds.dias_historico)} dias de '
             f'histórico · pacote {_e(cfg.get("rotulo", ""))}</p></div>'
             '<button class="print no-print" onclick="window.print()">Imprimir / salvar PDF</button></div>')
    if demo:
        p.append('<div class="demo"><b>Dados de demonstração.</b> Lojas, produtos, marcas, vendedores e números '
                 'são fictícios.</div>')
    if ds.avisos:
        p.append('<div class="avisos"><b>Atenção com os dados</b><ul>'
                 + "".join(f"<li>{_e(a)}</li>" for a in ds.avisos) + "</ul></div>")

    # ---------------------------------------------------------------- indicadores
    kpis = [_kpi("Faturamento", fmt.reais(k["faturamento"]), f"últimos {k['dias']} dias"),
            _kpi("Ticket médio", fmt.reais(k["ticket_medio"]), f"{fmt.inteiro(k['vendas'])} vendas")]
    if k["margem"] is not None:
        kpis.append(_kpi("Margem bruta", fmt.pct(k["margem"] * 100), "sobre o faturamento"))
    kpis.append(_kpi("Dinheiro parado", fmt.reais(parado["total"]),
                     f"{fmt.pct(parado['pct_do_estoque'] * 100)} do estoque · {fmt.inteiro(parado['itens'])} itens"))
    kpis.append(_kpi("Itens em risco de faltar", fmt.inteiro(ruptura["itens"]),
                     f"venda em risco {fmt.reais(ruptura['venda_em_risco'])}"))
    if perdidas:
        kpis.append(_kpi("Vendas perdidas", fmt.reais(perdidas["valor_estimado"]),
                         f"{fmt.inteiro(perdidas['ocorrencias'])} registros"))
    if orc:
        kpis.append(_kpi("Conversão de orçamentos", fmt.pct(orc["taxa"] * 100),
                         f"{fmt.inteiro(orc['orcamentos'])} orçamentos"))
    p.append(f'<div class="kpis">{"".join(kpis)}</div>')

    # ---------------------------------------------------------------- o que fazer agora
    p.append("<h2>O que fazer agora</h2><p class='sub'>Resumo e prioridades, ordenados pelo impacto em reais.</p>")
    p.append(f'<div class="card resumo">{_e(ins["resumo"])}</div>')
    for a in ins["alertas"]:
        p.append(f'<div class="card alerta"><span class="tag">{a["prioridade"]}. {_e(a["titulo"])}</span>'
                 f'<div>{_e(a["por_que"])}</div><div class="acao"><b>O que fazer:</b> {_e(a["acao"])}</div></div>')
    if ins["oportunidades"]:
        p.append("<h3>Oportunidades</h3><div class='card'>" + "".join(
            f"<p style='margin:4px 0'>{_e(o['texto'])} <span class='nota'>{_e(o['acao'])}</span></p>"
            for o in ins["oportunidades"]) + "</div>")

    # ---------------------------------------------------------------- dinheiro parado
    p.append(f"<h2>Dinheiro parado em estoque</h2><p class='sub'>Itens com estoque e sem venda há "
             f"{parado['dias']} dias ou mais, valorizados a custo.</p>")
    if res["parado_itens"].empty:
        motivo = ("Nenhum item parado." if parado["historico_suficiente"] else
                  f"O histórico tem menos de {parado['dias']} dias: ainda não dá para dizer o que está parado.")
        p.append(f"<div class='card'>{motivo}</div>")
    else:
        cat = [(r.categoria, r.valor_parado) for r in parado["por_categoria"].head(6).itertuples()]
        p.append(f"<div class='card'><h3 style='margin-top:0'>Por categoria</h3>{_barras(cat)}"
                 "<h3>Maiores itens parados</h3>")
        linhas = [[_e(r.descricao), _e(getattr(r, "categoria", "")), fmt.inteiro(r.quantidade_atual),
                   "sem venda no período" if r.nunca_vendeu else fmt.inteiro(r.dias_sem_venda),
                   fmt.reais(r.valor_parado)] for r in res["parado_itens"].head(15).itertuples()]
        p.append(_tabela([("Item", False), ("Categoria", False), ("Qtd", True), ("Sem venda há (dias)", True),
                          ("Valor parado", True)], linhas))
        if parado["valor_sempre_mantenho"]:
            p.append(f"<p class='nota'>Fora da conta: {fmt.reais(parado['valor_sempre_mantenho'])} em itens "
                     "marcados como 'sempre mantenho'.</p>")
        p.append("</div>")

    # ---------------------------------------------------------------- itens que vão faltar
    p.append(f"<h2>Itens que vão faltar</h2><p class='sub'>Classes A e B cujo estoque dura menos que o prazo do "
             f"fornecedor mais {fmt.inteiro(ruptura['seguranca'])} dias. Compra sugerida: cobre "
             f"{fmt.inteiro(ruptura['alvo'])} dias de venda além do prazo.</p>")
    if res["ruptura_itens"].empty:
        p.append("<div class='card'>Nenhum item importante em risco de faltar.</div>")
    else:
        linhas = [[_e(r.descricao), f'<span class="badge cl-{r.classe}">{r.classe}</span>',
                   fmt.inteiro(r.quantidade_atual), fmt.dias(r.cobertura_dias), fmt.numero(r.venda_diaria, 2),
                   fmt.inteiro(r.qtd_sugerida), fmt.reais(r.valor_compra), fmt.reais(r.venda_em_risco)]
                  for r in res["ruptura_itens"].head(15).itertuples()]
        p.append("<div class='card'>" + _tabela(
            [("Item", False), ("Classe", False), ("Estoque", True), ("Dura (dias)", True), ("Venda/dia", True),
             ("Comprar (un.)", True), ("Custo da compra", True), ("Venda em risco", True)], linhas)
            + f"<p class='nota'>Total sugerido para os itens em risco: <b>{fmt.reais(ruptura['compra_sugerida'])}</b>."
              "</p></div>")

    # ---------------------------------------------------------------- curva ABC
    p.append("<h2>Curva ABC</h2><p class='sub'>Poucos itens sustentam a maior parte do faturamento. "
             "Os da classe A não podem faltar.</p><div class='card'>" + _svg_abc(res["abc"])
             + "<p class='nota'>Horizontal: % dos itens (do mais ao menos vendido). Vertical: % do faturamento "
               "acumulado.</p>")
    linhas = [[f'<span class="badge cl-{c}">{c}</span>', fmt.inteiro(r.itens), fmt.pct(r.pct_itens * 100),
               fmt.reais(r.faturamento), fmt.pct(r.pct_valor * 100)]
              for c, r in zip(res["resumo_abc"].index, res["resumo_abc"].itertuples())]
    p.append(_tabela([("Classe", False), ("Itens", True), ("% dos itens", True), ("Faturamento", True),
                      ("% do faturamento", True)], linhas) + "</div>")

    # ---------------------------------------------------------------- giro
    giro = res["giro"]["categoria"]
    if not giro.empty:
        linhas = [[_e(r.categoria), fmt.reais(r.estoque_custo), fmt.reais(r.cmv_anual), fmt.numero(r.giro_anual, 1),
                   fmt.inteiro(r.cobertura_dias)] for r in giro.itertuples()]
        p.append("<h2>Giro e dias de estoque por categoria</h2><p class='sub'>Giro anual = venda a custo "
                 "anualizada ÷ valor do estoque atual.</p><div class='card'>" + _tabela(
                     [("Categoria", False), ("Estoque a custo", True), ("Venda a custo/ano", True),
                      ("Giro/ano", True), ("Estoque dura (dias)", True)], linhas) + "</div>")

    # ---------------------------------------------------------------- vendas perdidas
    if perdidas:
        p.append("<h2>Vendas perdidas e devoluções</h2><p class='sub'>Registros do balcão: o cliente pediu e não "
                 "saiu vendido (ou voltou por incompatibilidade).</p><div class='card'>")
        p.append(_barras([(r.rotulo, r.casos) for r in perdidas["por_motivo"].itertuples()],
                         formatar=lambda v: f"{fmt.inteiro(v)} {'caso' if v == 1 else 'casos'}"))
        linhas = [[_e(r.descricao), fmt.inteiro(r.ocorrencias), fmt.inteiro(r.quantidade), fmt.reais(r.valor)]
                  for r in perdidas["ranking"].itertuples()]
        p.append("<h3>Itens que mais escaparam</h3>" + _tabela(
            [("Item", False), ("Vezes", True), ("Qtd", True), ("Valor estimado", True)], linhas))
        if not perdidas["devolucoes_por_fornecedor"].empty:
            linhas = [[_e(r.fornecedor), fmt.inteiro(r.casos)]
                      for r in perdidas["devolucoes_por_fornecedor"].itertuples()]
            p.append("<h3>Devoluções por incompatibilidade, por fornecedor</h3>"
                     + _tabela([("Fornecedor", False), ("Casos", True)], linhas))
        p.append("</div>")

    # ---------------------------------------------------------------- equipe e orçamentos
    vend = res["vendedores"]
    if vend is not None or orc:
        p.append("<h2>Equipe e orçamentos</h2><p class='sub'>Desempenho por vendedor e itens que viram orçamento "
                 "mas não viram venda.</p><div class='card'>")
        if vend is not None:
            conv = {}
            if orc and orc["por_vendedor"] is not None:
                conv = orc["por_vendedor"].set_index("vendedor")["taxa"].to_dict()
            colunas = [("Vendedor", False), ("Vendas", True), ("Faturamento", True), ("Ticket médio", True),
                       ("Itens por venda", True)] + ([("Conversão de orçamentos", True)] if conv else [])
            linhas = [[_e(r.vendedor), fmt.inteiro(r.vendas), fmt.reais(r.faturamento), fmt.reais(r.ticket_medio),
                       fmt.numero(r.itens_por_venda, 1)]
                      + ([fmt.pct(conv[r.vendedor] * 100) if r.vendedor in conv else "—"] if conv else [])
                      for r in vend.itertuples()]
            p.append(_tabela(colunas, linhas))
        if orc and not orc["top_nao_convertidos"].empty:
            linhas = [[_e(r.descricao), fmt.inteiro(r.vezes), fmt.reais(r.valor)]
                      for r in orc["top_nao_convertidos"].itertuples()]
            p.append("<h3>Itens mais orçados e não vendidos</h3>"
                     + _tabela([("Item", False), ("Orçamentos", True), ("Valor", True)], linhas))
        p.append("</div>")

    # ---------------------------------------------------------------- dia e hora
    if res["dia_hora"]:
        p.append("<h2>Quando a loja vende mais</h2><p class='sub'>Faturamento por dia da semana e hora.</p>"
                 "<div class='card'>" + _mapa_dia_hora(res["dia_hora"])
                 + "<p class='nota'>Valores em R$ mil faturados em cada janela (soma do período). Toque numa "
                   "célula para ver o detalhe.</p></div>")

    cortes = cfg["corte_abc"]
    p.append("<div class='rodape'><b>Como os números são calculados.</b> Tudo é calculado por regras fixas, não "
             f"por estimativa de IA. Curva ABC: A até {fmt.inteiro(cortes[0] * 100)}% do faturamento acumulado, "
             f"B até {fmt.inteiro(cortes[1] * 100)}%. Venda diária: média dos últimos {cfg['janela_venda_dias']} dias. "
             f"Prazo padrão do fornecedor: {cfg['lead_time_dias']} dias. <br><b>Limitações desta versão:</b> o giro "
             "usa o estoque de hoje (não há histórico de estoque); a venda diária inclui dias em que o item estava "
             "em falta, o que subestima a demanda real desses itens; sazonalidade mensal exige 12 meses de "
             "histórico e ainda não está incluída.</div>")

    titulo = f"Diagnóstico de estoque e vendas - {_e(ds.nome_loja)}"
    return ('<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            f"<title>{titulo}</title><style>\n{_CSS}</style></head><body><div class=\"wrap\">"
            + "".join(p) + "</div></body></html>")
