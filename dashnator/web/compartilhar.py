"""Compartilhar o resumo: texto para copiar e link wa.me pré-preenchido. Sem API de WhatsApp:
quem envia é o dono, pelo próprio aparelho."""
from urllib.parse import quote


def texto_para_compartilhar(insights: dict, loja: str, dados_ate: str) -> str:
    """Resumo e ações em texto simples. Só reaproveita frases já verificadas (nenhum número novo)."""
    linhas = [f"*Dashnator - {loja}* (dados até {dados_ate})", "", insights["resumo"]]
    if insights["alertas"]:
        linhas += ["", "*O que fazer agora:*"]
        linhas += [f"• {a['titulo']}: {a['acao']}" for a in insights["alertas"]]
    return "\n".join(linhas)


def link_whatsapp(texto: str) -> str:
    return "https://wa.me/?text=" + quote(texto, safe="")
