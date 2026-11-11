"""Linha de comando: `python -m dashnator demo` e `python -m dashnator report`."""
import argparse
import json
import sys
from pathlib import Path

from dashnator.config import carregar_nicho
from dashnator.core.importer import ErroDeImportacao, carregar_dataset
from dashnator.demo.generate import NOME_LOJA_DEMO, gerar_dados
from dashnator.diagnostico import diagnosticar
from dashnator.report.html import render


def para_csv(df) -> bytes:
    """Uma tabela no formato que uma loja exportaria: ponto e vírgula, vírgula decimal, datas dd/mm/aaaa."""
    df = df.copy()
    if "data_hora" in df:
        df["data_hora"] = df["data_hora"].dt.strftime("%d/%m/%Y %H:%M")
    for c in df.columns:
        if df[c].dtype == bool:
            df[c] = df[c].map({True: "Sim", False: "Não"})
    return df.to_csv(sep=";", decimal=",", index=False).encode("utf-8-sig")


def exportar_csv(dados: dict, pasta: Path) -> None:
    """Grava cada tabela dos dados em <pasta>/<nome>.csv."""
    pasta.mkdir(parents=True, exist_ok=True)
    for nome, df in dados.items():
        (pasta / f"{nome}.csv").write_bytes(para_csv(df))


def _demo(args) -> None:
    saida = Path(args.out)
    dados = gerar_dados()
    exportar_csv(dados, saida / "csv")
    ds = carregar_dataset(dados["vendas"], dados["estoque"], dados["orcamentos"], dados["perdidas"],
                          nome_loja=NOME_LOJA_DEMO)
    d = diagnosticar(ds, carregar_nicho(args.nicho))
    arquivo = saida / "demo.html"
    arquivo.write_text(render(d.ds, d.cfg, d.res, d.insights, demo=True), encoding="utf-8")
    print(f"Demo gerada em {arquivo} (dados fictícios em {saida / 'csv'}).")


def _report(args) -> None:
    mapeamentos = json.loads(Path(args.mapping).read_text(encoding="utf-8")) if args.mapping else None
    cfg = carregar_nicho(args.nicho)
    ds = carregar_dataset(args.vendas, args.estoque, args.orcamentos, args.perdidas, mapeamentos=mapeamentos,
                          nome_loja=args.loja, min_historico_dias=cfg["min_historico_dias"])
    d = diagnosticar(ds, cfg)
    saida = Path(args.out)
    saida.mkdir(parents=True, exist_ok=True)
    arquivo = saida / "relatorio.html"
    arquivo.write_text(render(d.ds, d.cfg, d.res, d.insights), encoding="utf-8")
    print(f"Relatório gerado em {arquivo}.")
    for aviso in ds.avisos:
        print(f"  aviso: {aviso}")


def main(argv=None) -> None:
    for fluxo in (sys.stdout, sys.stderr):  # acentos no terminal do Windows
        if hasattr(fluxo, "reconfigure"):
            fluxo.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(prog="dashnator", description="Diagnóstico de estoque e vendas para varejo.")
    sub = parser.add_subparsers(dest="comando", required=True)
    demo = sub.add_parser("demo", help="gera dados fictícios e o relatório de demonstração")
    demo.add_argument("--out", default="saida")
    demo.add_argument("--nicho", default="autopecas")
    demo.set_defaults(func=_demo)
    rep = sub.add_parser("report", help="gera o relatório a partir do export de uma loja")
    rep.add_argument("--vendas", required=True)
    rep.add_argument("--estoque", required=True)
    rep.add_argument("--orcamentos")
    rep.add_argument("--perdidas")
    rep.add_argument("--mapping", help="JSON com o mapeamento de colunas")
    rep.add_argument("--loja", default="Loja")
    rep.add_argument("--nicho", default="autopecas")
    rep.add_argument("--out", default="saida")
    rep.set_defaults(func=_report)
    args = parser.parse_args(argv)
    try:
        args.func(args)
    except ErroDeImportacao as e:
        sys.exit(f"Não deu para ler os arquivos: {e}")
