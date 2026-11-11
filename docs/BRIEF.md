# Dashnator v2 — Brief (núcleo de varejo + pacote Autopeças)

> Documento para colocar na pasta do projeto e usar como contexto no Claude Code.
> Status: v0 construída e testada (importador, 6 análises, texto por regras com verificador de números,
> relatório HTML, gerador de dados fictícios, 25 testes). Formato de arquivos ainda GENÉRICO (sem export real
> de nenhum ERP). Próximo passo: etapa 1 de `ROTEIRO_PROMPTS.md` (primeira loja real). Atualizado com a
> pesquisa de dores do varejo de autopeças.
> 11/11/2026: o pacote `dashnator/` foi reconstruído a partir dos testes, deste brief e do relatório de exemplo
> (o código original não estava na pasta). Painel web de apresentação em Streamlit (`streamlit_app.py`), com
> login único `teste`/`teste`, demonstração, envio de arquivos, lista de compra em Excel e compartilhar por
> `wa.me`; 35 testes. Por decisão do dono, a apresentação web veio antes da primeira loja real e usa Streamlit
> no lugar do FastAPI da seção 8. Login por loja e dados separados por conta continuam para a v1.

---

## 1. Visão

Painel web que o dono de uma loja de autopeças abre para saber, em 1 minuto:
**onde está o dinheiro parado, o que vai faltar, o que ele está deixando de vender e o que fazer hoje.**

Não é "mais um dashboard": é um painel com **recomendações em português simples**, apoiadas em números
calculados por código (nunca inventados pelo LLM).

### Princípios
1. **Cálculo em código, texto no LLM.** Toda métrica (ABC, giro, cobertura, capital parado) é calculada
   de forma determinística. O LLM só recebe os resultados agregados e redige explicação + ação sugerida.
2. **Custo baixo de LLM.** O texto é gerado 1 vez por upload/versão de dados e guardado em cache.
   O LLM nunca recebe linhas brutas de venda.
3. **Privacidade por padrão.** O sistema não precisa de dados pessoais de clientes (nome, CPF, telefone).
   O importador ignora colunas fora do mapeamento e avisa se detectar padrão de CPF/CNPJ/telefone.
4. **Núcleo genérico + pacote de nicho.** O núcleo faz upload, mapeamento, painel e camada de insights.
   O pacote "autopeças" define campos, análises ativas, limiares e instruções do LLM (arquivo de configuração).
5. **Não ser burro com giro lento.** Autopeças precisa manter peça de baixo giro para ser loja completa.
   O dono pode marcar itens como **"sempre mantenho"**; eles saem dos alertas de capital parado.

### 1.1 Dores pesquisadas e o que o produto faz com cada uma
(Fontes: imprensa do setor, blogs de ERPs, Reclame Aqui, estudos de caso. Falta a voz direta do lojista:
tratar como hipóteses e validar nas visitas pedindo ao dono para ranquear as dores.)

| # | dor | evidência | no Dashnator |
|---|---|---|---|
| 1 | Estoque: capital parado e peça faltando | forte | NÚCLEO da v1 |
| 2 | Peça errada / aplicação / devolução | forte (mais no e-commerce) | motivo "devolução por incompatibilidade" em vendas perdidas |
| 3 | Marketplaces comprimindo preço e margem | forte | fora da v1; margem por item já aparece |
| 4 | Equipe de balcão (qualificação, rotatividade) | média/forte | ranking de vendedores + conversão de orçamento |
| 5 | Fiscal (ST, CEST, IBS/CBS) | forte, mas periférica | FORA de escopo (outros produtos já miram nisso) |
| 6 | Prazo e capital de giro (oficinas) | média (fontes de quem vende crédito) | aging de contas a receber na v1.5 |

---

## 2. Escopo por etapa

### v0 — Demo com dados fictícios (para levar às lojas) — CONSTRUÍDA
- Gerador de dados sintéticos (seção 9).
- Relatório HTML autossuficiente (funciona offline, no celular, imprime em PDF) com as análises 1–7 da seção 5.
- Texto de insights gerado por regras (sem LLM), no mesmo formato JSON que o LLM vai usar na v1.
- O MESMO código roda com o export real de uma loja: é o "diagnóstico" que se devolve ao dono.
- Objetivo: mostrar o conceito no celular/notebook em 3 minutos.

### v1 — Upload real
- Upload de Excel/CSV (vendas, estoque, opcional orçamentos) + mapeamento de colunas salvo por loja.
- Todas as análises da seção 5 + registro de vendas perdidas.
- Texto de insights via LLM (seção 7) com cache.
- Uma loja = um espaço de dados. Login simples (e-mail + senha).

### v1.5
Aging de contas a receber (oficinas): faixas 1–15, 16–30, 31–60, 61–90 e 90+ dias, por cliente, com limite de crédito
sugerido. Entra só depois de validar com o dono que é dor real.

### Fora de escopo por enquanto
Integração direta com ERP/API, WhatsApp API, emissão fiscal e auditoria de NCM/CEST, catálogo de aplicação
de peças, multi-loja/rede, app mobile nativo, sugestão de preço, comparação com concorrentes/marketplaces.

---

## 3. Entradas (formato canônico)

O importador converte qualquer planilha para estas colunas via mapeamento por loja.

### vendas (obrigatório)
| coluna canônica | tipo | obrigatório | observação |
|---|---|---|---|
| data_hora | datetime | sim | sem hora, o módulo dia×hora fica desativado |
| documento | texto | sim | id da venda/cupom, agrupa itens |
| sku | texto | sim | código interno da peça |
| descricao | texto | sim | |
| quantidade | número | sim | |
| preco_unitario | número | sim | |
| custo_unitario | número | não | sem custo, margem fica desativada |
| categoria / marca | texto | não | |
| vendedor | texto | não | |

### estoque (obrigatório)
sku, descricao, quantidade_atual, custo_unitario, preco_venda, e opcionais: categoria, marca, fornecedor, lead_time_dias.

### orcamentos (opcional)
data_hora, documento, sku, quantidade, preco_unitario, convertido (sim/não ou status), vendedor.

### Qualidade de dados (mostrar banner no painel)
- < 90 dias de histórico: ABC/cobertura marcados como "pouco histórico".
- < 12 meses: sazonalidade desativada.
- SKUs de venda ausentes no estoque (e vice-versa): listar e contar.
- Quantidades negativas, preços zero, datas futuras: listar e excluir do cálculo.

---

## 4. Modelo de dados (mínimo)

`lojas`, `usuarios`, `mapeamentos` (loja, tipo_arquivo, json de colunas), `uploads` (loja, tipo, data, hash, versão),
`vendas`, `estoque`, `orcamentos`, `vendas_perdidas`, `config_itens` (loja, sku, sempre_mantenho),
`config_loja` (limiares, lead times), `insights` (loja, versão_dados, hash_config, json, texto, criado_em).

Cada novo upload cria uma **versão de dados**; o cache de insights é indexado por (versão_dados + hash da configuração).

---

## 5. Análises (v1)

Parâmetros padrão (todos configuráveis por loja): janela de venda = 90 dias; corte ABC = 80% / 95% acumulado;
encalhe = sem venda há 180 dias; lead time = 7 dias; cobertura alvo = 30 dias.

1. **Curva ABC** — ordenar SKUs por faturamento dos últimos 12 meses (ou todo o histórico, se menor);
   classe A até 80% acumulado, B até 95%, C o resto. Versão por margem bruta quando houver custo.
2. **Capital parado** — SKUs com estoque > 0 e sem venda há ≥ N dias (exceto "sempre mantenho").
   Valor imobilizado = quantidade_atual × custo_unitario. Mostrar total, por categoria/fornecedor e top 20 itens.
3. **Risco de ruptura + sugestão de compra** — para classes A e B:
   venda_diária = qtd vendida na janela ÷ dias da janela;
   cobertura_dias = quantidade_atual ÷ venda_diária;
   risco se cobertura_dias < lead_time + margem de segurança;
   qtd_sugerida = arredonda_para_cima(max(0, venda_diária × (lead_time + cobertura_alvo) − quantidade_atual));
   venda_em_risco = max(0, lead_time − cobertura_dias) × venda_diária × preço de venda.
   Limitação v1: sem histórico diário de estoque, dias de ruptura passada subestimam a venda diária. Avisar no painel.
4. **Giro e cobertura** por categoria, marca e fornecedor. Giro anual = CMV 12m ÷ estoque médio
   (v1: usa o estoque atual como aproximação e avisa isso).
5. **Vendas perdidas e devoluções** — registro rápido no painel (botão de um toque): sku ou descrição livre, quantidade,
   motivo (sem estoque / sem aplicação cadastrada / preço / devolução ou troca por incompatibilidade / outro).
   Ranking por frequência e valor estimado; devoluções por incompatibilidade também por fornecedor.
6. **Orçamentos não convertidos** (se houver arquivo) — taxa de conversão total e por vendedor;
   itens mais orçados e não vendidos.
7. **Dia × hora e vendedor** — heatmap de faturamento e de nº de vendas; ticket médio; ranking de vendedores.
   Módulo secundário (apoio à escala de balconistas).
8. **Sazonalidade** (só com ≥ 12 meses) — SKUs/categorias com pico recorrente por mês.

---

## 6. Telas

1. Upload e mapeamento (primeira vez: mapear colunas; depois: só arrastar o arquivo).
2. **Visão geral**: KPIs (faturamento, margem, capital parado, itens em risco, vendas perdidas) + resumo de IA.
3. Estoque: capital parado, risco de ruptura, lista de compra sugerida (exportável).
4. Curva ABC.
5. Vendas: dia×hora, vendedores, ticket médio.
6. Vendas perdidas e orçamentos.
7. Configurações: limiares, lead times, "sempre mantenho".

Lista de compra e relatórios exportam para Excel/PDF. O resumo tem botão "copiar" e link `wa.me` com texto
pré-preenchido (o dono envia por conta própria; sem API de WhatsApp).

---

## 7. Camada de IA

**Entrada** (JSON agregado, nunca linhas brutas): KPIs do período, top 10–20 itens de cada lista
(capital parado, risco de ruptura, vendas perdidas), totais por categoria, avisos de qualidade de dados.

**Saída esperada** (JSON):
```json
{
  "resumo": "até 4 frases",
  "alertas": [{"tipo": "capital_parado|ruptura|venda_perdida|orcamento", "prioridade": 1,
               "itens": ["sku1"], "por_que": "...", "acao": "..."}],
  "oportunidades": [{"texto": "...", "acao": "..."}]
}
```

**Regras do prompt:**
- Português do Brasil, linguagem de balcão, sem jargão (explicar "cobertura" como "dias de estoque").
- Usar SOMENTE números presentes na entrada. Nunca estimar ou inventar.
- No máximo 5 alertas, ordenados por impacto em reais.
- Cada alerta tem causa e ação concreta ("comprar X unidades", "fazer promoção do item Y", "rever o fornecedor Z").
- Respeitar "sempre mantenho" e avisar quando os dados forem insuficientes.

**Verificação pós-geração:** extrair os números do texto e conferir se existem na entrada; se algum não existir,
regenerar uma vez; persistindo, exibir só os números calculados, sem texto livre.

**Custo:** modelo menor; 1 chamada por versão de dados; cache; nenhuma chamada ao abrir o painel.

---

## 8. Arquitetura sugerida (trocável)

- Python: pandas (ou DuckDB) para cálculo; FastAPI para API; SQLite para persistência na v1.
- Front leve: HTML + HTMX + Chart.js (ou o que você preferir no Claude Code).
- Pacote de nicho = arquivo de configuração (YAML): campos aceitos, análises ativas, limiares padrão,
  instruções específicas para o LLM. Novo nicho = novo YAML, não novo código.
- Testes: cada análise tem teste com um conjunto pequeno de dados em que o resultado é conhecido à mão.

Estrutura inicial:
```
dashnator/
  config.py    carrega o YAML do nicho
  core/        importador, qualidade de dados, período            (mapeamento por loja e versões: v1)
  analyses/    abc.py, capital_parado.py, ruptura.py, giro.py, perdidas.py, dia_hora.py   (sazonal.py: v1.x)
  ai/          payload.py, template_insights.py, verify.py, fmt.py   (llm.py e cache: v1)
  report/      html.py (relatório autossuficiente)
  demo/        gerador de dados sintéticos
  cli.py       comandos demo e report
  web/         rotas e telas                                       (v1)
niches/        autopecas.yaml
tests/
docs/
```

---

## 9. Dados sintéticos para a demo (v0)

Gerador com semente fixa, 100% fictício (marcas e códigos inventados):
- ~800 SKUs em ~12 categorias; descrições do tipo "Pastilha de freio dianteira — Marca A".
- 12 meses de vendas, ~15–25 mil linhas; distribuição de Pareto (poucos SKUs com a maior parte do faturamento).
- Mais vendas em dias úteis; picos de hora em duas faixas do dia (valores fictícios).
- ~10% dos SKUs encalhados (estoque alto, sem venda há 6+ meses).
- ~5% dos SKUs classe A com cobertura baixa (para disparar alertas de ruptura).
- ~30 vendas perdidas e ~600 orçamentos, ~65% convertidos.
- Marcar claramente na interface: **"Dados de demonstração"**.

---

## 10. Validação com lojas (resumo)

Fluxo: visita com a demo → pedir export dos últimos 12 meses (vendas + estoque, sem dados pessoais de clientes)
→ devolver um diagnóstico em PDF em poucos dias, rodando o próprio código do Dashnator → conversar sobre uso e preço.
Antes de construir telas bonitas, o diagnóstico em PDF já testa se o dono acha o conteúdo valioso.

Sinais de sucesso: o dono reconhece os números ("é isso mesmo"), age em pelo menos 1 recomendação,
e topa ver de novo no mês seguinte.

---

## 11. Perguntas em aberto

1. Qual ERP a primeira loja usa e o que ele exporta de fato?
2. O ERP registra orçamentos/pré-vendas com histórico que dê para exportar?
3. A loja tem o custo atualizado no cadastro?
4. Quanto o dono pagaria por mês e qual valor ele enxerga como "ganho" (capital liberado, vendas recuperadas)?
5. Como o dono prefere acompanhar: abre o painel sozinho ou precisa de um lembrete (e-mail)?
