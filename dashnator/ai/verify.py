"""Confere que todo número citado num texto existe no payload.

Vale para o texto por regras e, depois, para o texto do LLM: número que não está no payload não vai
para a tela. Números dentro de textos do payload (ex.: 'Aplic. V07') também contam.
"""
import re

_NUMERO = re.compile(r"\d{1,3}(?:\.\d{3})+(?:,\d+)?|\d+(?:,\d+)?")


def _valor(token: str) -> tuple[float, int]:
    """'1.234,5' -> (1234.5, 1 casa decimal)"""
    casas = len(token.split(",")[1]) if "," in token else 0
    return float(token.replace(".", "").replace(",", ".")), casas


def _numeros_do_payload(payload) -> list[float]:
    numeros: list[float] = []

    def andar(x):
        if isinstance(x, bool) or x is None:
            return
        if isinstance(x, (int, float)):
            numeros.append(float(x))
        elif isinstance(x, str):
            numeros.extend(_valor(t)[0] for t in _NUMERO.findall(x))
        elif isinstance(x, dict):
            for v in x.values():
                andar(v)
        elif isinstance(x, (list, tuple)):
            for v in x:
                andar(v)

    andar(payload)
    return numeros


def numeros_nao_verificados(texto: str, payload) -> list[str]:
    """Números do texto (como foram escritos) que não existem no payload. Lista vazia = texto aprovado.

    Um número do texto confere quando algum número do payload, arredondado para as mesmas casas
    decimais, dá exatamente ele (R$ 1.234 confere com 1234.4 do payload; 25,3% não confere com 25.2).
    """
    do_payload = _numeros_do_payload(payload)
    por_casas: dict[int, set[str]] = {}
    fora = []
    for token in _NUMERO.findall(texto):
        valor, casas = _valor(token)
        if casas not in por_casas:
            por_casas[casas] = {f"{p:.{casas}f}" for p in do_payload}
        if f"{valor:.{casas}f}" not in por_casas[casas]:
            fora.append(token)
    return fora


def textos_do_insight(insight: dict) -> str:
    """Todo o texto livre de um insight, numa string só, para verificar."""
    partes = [insight.get("resumo", "")]
    for a in insight.get("alertas", []):
        partes += [a.get("titulo", ""), a.get("por_que", ""), a.get("acao", "")]
    for o in insight.get("oportunidades", []):
        partes += [o.get("texto", ""), o.get("acao", "")]
    return "\n".join(p for p in partes if p)
