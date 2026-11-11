"""Login da apresentação: um usuário e uma senha, configuráveis sem mexer no código.

Padrão: teste / teste. Para trocar, defina DASHNATOR_USUARIO e DASHNATOR_SENHA nos segredos do
Streamlit (ou em variáveis de ambiente). É uma porta de entrada para a demonstração, não o login
por loja da v1 (docs/BRIEF.md): não há cadastro nem separação de dados por conta.
"""
import hmac
import os
from collections.abc import Mapping

USUARIO_PADRAO = "teste"
SENHA_PADRAO = "teste"
MAX_TENTATIVAS = 5


def credenciais(segredos: Mapping | None = None) -> tuple[str, str]:
    """(usuário, senha) válidos: segredos do Streamlit, depois variáveis de ambiente, depois o padrão."""
    segredos = segredos if segredos is not None else {}

    def ler(chave: str, padrao: str) -> str:
        valor = segredos.get(chave) if chave in segredos else os.environ.get(chave)
        return str(valor) if valor else padrao

    return ler("DASHNATOR_USUARIO", USUARIO_PADRAO), ler("DASHNATOR_SENHA", SENHA_PADRAO)


def confere(usuario: str, senha: str, segredos: Mapping | None = None) -> bool:
    """True se usuário e senha batem. Comparação em tempo constante."""
    certo_usuario, certa_senha = credenciais(segredos)
    ok_usuario = hmac.compare_digest(usuario.strip().lower().encode(), certo_usuario.strip().lower().encode())
    ok_senha = hmac.compare_digest(senha.encode(), certa_senha.encode())
    return ok_usuario and ok_senha
