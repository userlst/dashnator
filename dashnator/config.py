"""Carrega o pacote de nicho (niches/*.yaml). Novo nicho = novo YAML, sem mudar as análises."""
from pathlib import Path

import yaml

PASTA_NICHOS = Path(__file__).resolve().parent.parent / "niches"

OBRIGATORIOS = ("janela_venda_dias", "corte_abc", "encalhe_dias", "lead_time_dias",
                "margem_seguranca_dias", "cobertura_alvo_dias", "min_historico_dias")


def carregar_nicho(nome: str = "autopecas", sobrescrever: dict | None = None) -> dict:
    """Parâmetros do nicho. `sobrescrever` troca limiares (ajustes da loja)."""
    arquivo = PASTA_NICHOS / f"{nome}.yaml"
    if not arquivo.exists():
        raise FileNotFoundError(f"Pacote de nicho não encontrado: {arquivo.name}")
    cfg = yaml.safe_load(arquivo.read_text(encoding="utf-8"))
    faltando = [c for c in OBRIGATORIOS if c not in cfg]
    if faltando:
        raise ValueError(f"{arquivo.name}: faltam os parâmetros {', '.join(faltando)}")
    cfg.setdefault("rotulo", nome)
    cfg.setdefault("motivos_perdida", {})
    cfg.update(sobrescrever or {})
    return cfg
