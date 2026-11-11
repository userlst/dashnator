"""Texto de insights por regras (sem LLM), no mesmo formato JSON que o LLM vai devolver.

Entrada: só o payload de ai/payload.py. Todo número escrito aqui sai do payload e é formatado por
ai/fmt.py; por isso o texto sempre passa em ai/verify.py. É também o texto de reserva do LLM.
"""
from dashnator.ai import fmt

MAX_ALERTAS = 5


def _plural(n: int, um: str, varios: str) -> str:
    return f"{fmt.inteiro(n)} {um if n == 1 else varios}"


def _lista(partes: list[str]) -> str:
    return "; ".join(partes)


def _resumo(p: dict) -> str:
    k, per = p["kpis"], p["periodo"]
    frases = [f"{p['loja']} faturou {fmt.reais(k['faturamento_12m'])} nos últimos {per['dias_dos_indicadores']} dias, "
              f"em {_plural(k['vendas'], 'venda', 'vendas')} (ticket médio de {fmt.reais(k['ticket_medio'])})."]
    if k["itens_parados"]:
        frases.append(f"Há {fmt.reais(k['dinheiro_parado'])} parados em estoque "
                      f"({fmt.pct(k['pct_parado'])} do valor estocado).")
    if k["itens_em_risco"]:
        frases.append(f"{_plural(k['itens_em_risco'], 'item importante tende', 'itens importantes tendem')} a faltar "
                      f"antes da próxima reposição, com cerca de {fmt.reais(k['venda_em_risco'])} em vendas em risco.")
    if k.get("perdidas_registros"):
        frases.append(f"{_plural(k['perdidas_registros'], 'venda perdida foi registrada', 'vendas perdidas foram registradas')} "
                      f"(estimativa de {fmt.reais(k['perdidas_valor'])}).")
    if not per["historico_suficiente"]:
        frases.append(f"Atenção: o histórico tem só {per['dias_de_historico']} dias; com menos de "
                      f"{per['historico_minimo_dias']} dias os números de estoque são pouco confiáveis.")
    return " ".join(frases)


def _alerta_parado(p: dict) -> dict | None:
    k = p["kpis"]
    if not k["itens_parados"]:
        return None
    maiores = [f"{i['descricao']} ({fmt.reais(i['valor'])})" for i in p["parado_top"][:3]]
    return {
        "tipo": "capital_parado", "titulo": "Dinheiro parado",
        "itens": [i["sku"] for i in p["parado_top"][:3]],
        "por_que": (f"{fmt.reais(k['dinheiro_parado'])} estão parados em "
                    f"{_plural(k['itens_parados'], 'item', 'itens')} sem venda há {p['config']['encalhe_dias']} dias "
                    f"ou mais. Os maiores: {_lista(maiores)}."),
        "acao": ("Pare de recomprar esses itens, faça promoção ou negocie devolução com o fornecedor. "
                 "Peças que você quer sempre ter podem ser marcadas como 'sempre mantenho'."),
        "impacto_reais": k["dinheiro_parado"],
    }


def _alerta_ruptura(p: dict) -> dict | None:
    k, cfg = p["kpis"], p["config"]
    if not k["itens_em_risco"]:
        return None
    top = p["ruptura_top"][:3]

    def situacao(i):
        return "sem estoque" if i["estoque"] == 0 else f"estoque para {fmt.dias(i['dias_de_estoque'])} dias"

    urgentes = [f"{i['descricao']} ({situacao(i)})" for i in top]
    comprar = [f"{fmt.inteiro(i['comprar'])} un. de {i['descricao']}" for i in top if i["comprar"] > 0]
    acao = (f"Compre agora: {_lista(comprar)}. " if comprar else "") + (
        f"O total sugerido para todos os itens em risco é {fmt.reais(k['compra_sugerida'])}, "
        f"cobrindo {cfg['cobertura_alvo_dias']} dias de venda.")
    return {
        "tipo": "ruptura", "titulo": "Risco de faltar", "itens": [i["sku"] for i in top],
        "por_que": (f"{_plural(k['itens_em_risco'], 'item das classes A e B deve', 'itens das classes A e B devem')} "
                    f"acabar antes de o pedido chegar (prazo padrão de {cfg['prazo_padrao_dias']} dias). "
                    f"Venda em risco estimada: {fmt.reais(k['venda_em_risco'])}. Mais urgentes: {_lista(urgentes)}."),
        "acao": acao,
        "impacto_reais": k["venda_em_risco"],
    }


def _alerta_orcamentos(p: dict) -> dict | None:
    k, orc = p["kpis"], p.get("orcamentos")
    if not orc or not k.get("orcamentos_nao_convertidos_valor"):
        return None
    por_que = (f"{fmt.pct(k['conversao_pct'])} dos {_plural(k['orcamentos'], 'orçamento', 'orçamentos')} viraram "
               f"venda. Os não convertidos somam {fmt.reais(k['orcamentos_nao_convertidos_valor'])}.")
    if len(orc["por_vendedor"]) > 1:
        pior = min(orc["por_vendedor"], key=lambda v: v["conversao_pct"])
        por_que += f" Menor conversão: {pior['vendedor']} ({fmt.pct(pior['conversao_pct'])})."
    itens = []
    if orc["top_nao_convertidos"]:
        t = orc["top_nao_convertidos"][0]
        itens = [t["sku"]]
        por_que += (f" Item mais orçado e não vendido: {t['descricao']} "
                    f"({_plural(t['vezes'], 'orçamento', 'orçamentos')}).")
    return {
        "tipo": "orcamento", "titulo": "Orçamentos", "itens": itens, "por_que": por_que,
        "acao": ("Veja nos itens mais orçados se o problema é preço ou prazo e combine a abordagem de "
                 "fechamento com a equipe."),
        "impacto_reais": k["orcamentos_nao_convertidos_valor"],
    }


def _alerta_perdidas(p: dict) -> dict | None:
    k, per = p["kpis"], p.get("perdidas")
    if not per or not k.get("perdidas_registros"):
        return None
    por_que = (f"{_plural(k['perdidas_registros'], 'venda perdida registrada', 'vendas perdidas registradas')} "
               f"(cerca de {fmt.reais(k['perdidas_valor'])}).")
    if per["por_motivo"]:
        m = per["por_motivo"][0]
        por_que += f" Motivo mais frequente: {m['rotulo'].lower()} ({_plural(m['casos'], 'caso', 'casos')})."
    itens = []
    if per["top"]:
        t = max(per["top"], key=lambda i: i["vezes"])
        itens = [t["sku"]] if t["sku"] else []
        por_que += f" Item que mais escapou: {t['descricao']} ({_plural(t['vezes'], 'vez', 'vezes')})."
    return {
        "tipo": "venda_perdida", "titulo": "Vendas perdidas", "itens": itens, "por_que": por_que,
        "acao": ("Se o motivo é falta de estoque, inclua esses itens na próxima compra. Se é preço ou "
                 "aplicação, revise a tabela e o cadastro antes de repor."),
        "impacto_reais": k["perdidas_valor"],
    }


def _alerta_devolucoes(p: dict) -> dict | None:
    per = p.get("perdidas")
    if not per or not per["devolucoes"]:
        return None
    por_que = (f"{_plural(per['devolucoes'], 'devolução ou troca', 'devoluções ou trocas')} por peça "
               "incompatível com o veículo.")
    if per["devolucoes_por_fornecedor"]:
        f = per["devolucoes_por_fornecedor"][0]
        por_que += f" Fornecedor com mais casos: {f['fornecedor']} ({fmt.inteiro(f['casos'])})."
    return {
        "tipo": "venda_perdida", "titulo": "Devoluções por incompatibilidade", "itens": [], "por_que": por_que,
        "acao": ("Confira ano, versão e chassi antes de fechar a venda e cobre do fornecedor a revisão da "
                 "aplicação no catálogo."),
        "impacto_reais": per["devolucoes_valor"],
    }


def _oportunidades(p: dict) -> list[dict]:
    saida = []
    classe_a = next((c for c in p["abc"] if c["classe"] == "A"), None)
    if classe_a and classe_a["itens"]:
        saida.append({
            "texto": (f"{_plural(classe_a['itens'], 'item classe A concentra', 'itens classe A concentram')} "
                      f"{fmt.pct(classe_a['pct_faturamento'])} do faturamento."),
            "acao": "São os que não podem faltar: confira os dias de estoque deles toda semana."})
    picos = p.get("horarios_de_pico")
    if picos:
        horarios = _lista([f"{h['dia']} às {h['hora']}h" for h in picos])
        saida.append({"texto": f"Maior movimento de vendas: {horarios}.",
                      "acao": "Reforce o balcão nesses horários e evite deixar a equipe em reposição neles."})
    return saida


def gerar(payload: dict) -> dict:
    """{'resumo', 'alertas' (até 5, do maior impacto em reais para o menor), 'oportunidades'}"""
    candidatos = [f(payload) for f in (_alerta_parado, _alerta_ruptura, _alerta_orcamentos,
                                        _alerta_perdidas, _alerta_devolucoes)]
    alertas = sorted((a for a in candidatos if a), key=lambda a: a["impacto_reais"], reverse=True)[:MAX_ALERTAS]
    for posicao, alerta in enumerate(alertas, start=1):
        alerta["prioridade"] = posicao
    return {"resumo": _resumo(payload), "alertas": alertas, "oportunidades": _oportunidades(payload)}
