# Dashnator

Diagnóstico de estoque e vendas para varejo, com pacote inicial para **autopeças**.
O dono abre um painel (ou recebe um relatório em PDF) que mostra onde está o dinheiro parado, o que vai
faltar, o que ele está deixando de vender e quando a loja fatura mais. Os números são calculados por regras
fixas; a IA só escreve o resumo em português a partir de números já calculados.

## Começar em 2 minutos
```bash
python -m venv .venv && source .venv/bin/activate      # no Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m pytest -q
python -m dashnator demo --out saida
```
Abra `saida/demo.html` no navegador (funciona offline, no celular e imprime em PDF).

## Painel web (Streamlit)
```bash
streamlit run streamlit_app.py --server.address localhost
```
Abre em http://localhost:8501. Login da apresentação: `teste` / `teste`. O painel mostra a loja de demonstração
ou os arquivos que você enviar (vendas e estoque; orçamentos e vendas perdidas são opcionais), com as telas
Visão geral, Estoque, Curva ABC, Vendas, Perdidas e orçamentos e Relatório. Para publicar: `docs/DEPLOY.md`.

Já existe um exemplo pronto em `exemplo/` (`demo.html` e `demo.pdf`).
`saida/csv/` traz os mesmos dados fictícios nos arquivos que uma loja real exportaria.

## Rodar com o export de uma loja
```bash
python -m dashnator report --vendas vendas.csv --estoque estoque.csv \
       --orcamentos orcamentos.csv --perdidas perdidas.csv \
       --mapping mapeamento_loja.json --loja "Auto Peças Fulano" --out saida
```
`--orcamentos`, `--perdidas` e `--mapping` são opcionais. O mapeamento diz qual coluna do arquivo da loja
corresponde a cada coluna canônica:
```json
{"vendas": {"data_hora": "Data", "documento": "Pedido", "sku": "Código", "descricao": "Produto",
            "quantidade": "Qtd", "preco_unitario": "Preço Unit."},
 "estoque": {"sku": "Código", "descricao": "Produto", "quantidade_atual": "Saldo",
             "custo_unitario": "Custo", "preco_venda": "Preço"}}
```
Colunas com CPF, CNPJ, telefone, e-mail ou nome de cliente são descartadas automaticamente (com aviso).

## Mapa do código
```
dashnator/
  config.py            carrega niches/*.yaml (limiares do nicho)
  core/                importer.py (Excel/CSV → tabelas canônicas, qualidade de dados), periodo.py
  analyses/            abc, capital_parado, ruptura, giro, perdidas (+orçamentos), dia_hora (+vendedores)
  pipeline.py          roda todas as análises e devolve um dicionário de resultados
  ai/                  payload.py (JSON agregado), template_insights.py (texto por regras),
                       verify.py (confere números do texto), fmt.py (formatação pt-BR)
  report/html.py       relatório HTML autossuficiente
  demo/generate.py     gerador de dados fictícios (semente fixa)
  diagnostico.py       do conjunto de dados ao diagnóstico pronto (análises + payload + texto verificado)
  report/excel.py      lista de compra em Excel, uma aba por fornecedor
  web/                 acesso.py (login da apresentação), compartilhar.py (texto e link wa.me)
  cli.py               comandos demo e report
streamlit_app.py       painel web (Streamlit)
niches/autopecas.yaml  parâmetros do pacote autopeças
tests/                 testes com resposta conhecida (25) e do painel (10)
docs/                  BRIEF.md, ROTEIRO_PROMPTS.md, KIT_VISITA.md, DEPLOY.md
```

## Próximos passos
Siga `docs/ROTEIRO_PROMPTS.md` com o Claude Code aberto nesta pasta. As regras do projeto estão em `CLAUDE.md`.
Para levar às lojas: `docs/KIT_VISITA.md`.
