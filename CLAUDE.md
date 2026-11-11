# Dashnator — regras do projeto (leia antes de qualquer tarefa)

Painel/diagnóstico de estoque e vendas para varejo, começando por **autopeças**. Dono do projeto: Lustoza.
Contexto completo do produto: `docs/BRIEF.md`. Ordem de construção: `docs/ROTEIRO_PROMPTS.md`.

## Comandos
```bash
pip install -r requirements.txt
python -m pytest -q                         # tudo precisa passar antes de qualquer entrega
python -m dashnator demo --out saida        # dados fictícios + saida/demo.html
python -m dashnator report --vendas v.csv --estoque e.csv --loja "Nome" --out saida   # export real
streamlit run streamlit_app.py --server.address localhost    # painel web (login da apresentação: teste / teste)
```
Publicação: `docs/DEPLOY.md` (recomendado: Streamlit Community Cloud).

## Regras que não mudam
1. **Cálculo é determinístico (pandas); o LLM só redige.** Nenhum número vem do LLM. Ele recebe um JSON
   agregado (`ai/payload.py`), nunca linhas brutas, e devolve texto. Todo texto gerado passa por
   `ai/verify.py` (todo número citado tem que existir no payload); se falhar, regenera uma vez e, persistindo,
   cai no texto por regras (`ai/template_insights.py`).
2. **Português do Brasil** em toda interface, mensagem de erro e texto de IA. Linguagem de balcão: dizer
   "dias de estoque", não "cobertura"; "dinheiro parado", não "capital imobilizado". Formatação de números
   só via `ai/fmt.py` (R$ 1.234,56 / 25,2%).
3. **Privacidade:** nunca guardar nem enviar dados pessoais de clientes (CPF, CNPJ, telefone, e-mail, nome).
   O importador descarta essas colunas e avisa. Não registrar linhas de venda em logs.
4. **Sem API de WhatsApp.** Compartilhar = botão "copiar" + link `wa.me/?text=` pré-preenchido.
5. **Custo de IA baixo:** modelo menor, 1 chamada por versão dos dados, cache por (hash dos dados + hash da
   configuração), nenhuma chamada ao abrir o painel.
6. **Pacote de nicho = YAML** (`niches/*.yaml`). Novo nicho não pode exigir mudança nas análises.
7. **Todo cálculo novo nasce com teste de resposta conhecida** (conta feita à mão, em `tests/`). Sem teste, não entra.
8. **Dependência nova só com motivo claro**, e avisar o dono antes. Preferir o que já está em `requirements.txt`.
9. **Fora de escopo por enquanto** (não construir sem pedido explícito): integração direta com ERP, auditoria
   fiscal (NCM/CEST/ST), catálogo de aplicação de peças, multi-loja, app nativo, sugestão de preço,
   comparação com marketplaces.

## Fórmulas (fonte única — se mudar uma, mude aqui, no brief e nos testes)
- `venda_diaria` = quantidade vendida na janela (padrão 90 dias) ÷ dias da janela
- `cobertura_dias` = estoque ÷ venda_diaria
- Risco de ruptura = classe A ou B **e** cobertura < prazo do fornecedor + margem de segurança
- `qtd_sugerida` = arredonda_para_cima(max(0, venda_diaria × (prazo + cobertura_alvo) − estoque))
- `venda_em_risco` = max(0, prazo − cobertura) × venda_diaria × preço de venda
- ABC por faturamento em 12 meses: A até 80% do acumulado, B até 95%; o item que cruza o corte fica na classe de cima
- Capital parado = estoque > 0 e sem venda há ≥ 180 dias; itens `sempre_mantenho` ficam fora dos alertas
- Padrões: prazo 7 dias, margem de segurança 3 dias, cobertura alvo 30 dias (ver `niches/autopecas.yaml`)

## Convenções de código
- Python 3.13, pandas 3 (colunas de texto são `string`; cuidado com `NA`, use `.loc` para atribuir por máscara).
- Tabelas canônicas (colunas fixas) definidas em `core/importer.py`: `vendas`, `estoque`, `orcamentos`, `perdidas`.
- `fim_data(vendas)` (data da última venda) é a data de referência de todas as análises, nunca "hoje".
- A demo usa data de referência fixa (2026-11-10) e semente fixa: o resultado é reproduzível.
- Relatório HTML é autossuficiente: CSS inline, gráficos em SVG, sem CDN, sem JavaScript (só o botão de imprimir).
- Painel web = `streamlit_app.py` (Streamlit, decisão do dono em 11/11/2026 para a primeira apresentação; o brief
  previa FastAPI). Ele só monta a tela: todo número vem de `dashnator/diagnostico.py` (mesmo caminho do
  relatório) e toda formatação de `ai/fmt.py`. Peças testáveis ficam em `dashnator/web/` e `report/excel.py`.
- Login do painel: `dashnator/web/acesso.py`. Padrão `teste`/`teste`; troca-se por `DASHNATOR_USUARIO` e
  `DASHNATOR_SENHA` nos segredos do Streamlit. É uma porta de apresentação, não o login por loja da v1.
- Arquivos enviados pelo painel ficam só na memória da sessão (`st.session_state`), nunca em disco nem em cache global.

## Como trabalhar
- Antes de mudar uma análise: ler o teste dela. Depois de mudar: `python -m pytest -q` e regerar a demo.
- Conferir números do relatório contra um cálculo independente direto das vendas (ver `tests/test_verify_e_pipeline.py`).
- Ao terminar uma etapa do roteiro, atualizar o status no topo de `docs/BRIEF.md`.
- Se uma decisão do brief for contrariada pelos dados reais de uma loja, parar e propor a mudança em vez de contornar.
