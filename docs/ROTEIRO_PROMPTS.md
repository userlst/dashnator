# Roteiro: construindo o Dashnator com o Claude Code

Como usar: abra o Claude Code **dentro desta pasta** (ele lê o `CLAUDE.md` sozinho) e cole um prompt por vez,
na ordem. Só passe para o próximo quando o critério de pronto do atual estiver cumprido. Se algo travar, cole
o erro e peça para ele corrigir antes de seguir.

> Regra de ouro: **a etapa 1 depende de você ir a uma loja.** Não construa a parte web (etapa 3 em diante)
> antes de ter rodado o diagnóstico em pelo menos uma loja real. Os dados reais vão mudar o que importa.

---

## Etapa 0 — Conferir que tudo funciona (5 min)

```
Leia CLAUDE.md e README.md. Crie o ambiente virtual, instale o requirements.txt, rode os testes e gere a demo.
Depois me diga em 5 linhas o que o projeto faz hoje, o que está testado e o que ainda não existe.
```
**Pronto quando:** 25 testes passam e `saida/demo.html` abre no navegador. Abra no celular também.

---

## Etapa 1 — Primeira loja real (o passo mais importante)

Siga o `docs/KIT_VISITA.md`. Quando tiver os arquivos da loja, coloque numa pasta `dados_reais/` (ela está no
`.gitignore`, então nunca vai para o Git) e peça:

```
Estes são os arquivos exportados do ERP da loja "NOME": dados_reais/vendas.xlsx e dados_reais/estoque.xlsx.
1) Mostre as colunas e uma amostra de 5 linhas de cada (sem exibir nenhuma coluna com dados de cliente).
2) Proponha o mapeamento de colunas e salve em dados_reais/mapeamento_NOME.json.
3) Rode o relatório e liste TODOS os avisos de qualidade de dados.
4) Confira 3 números do relatório contra um cálculo independente direto dos arquivos (faturamento, valor
   parado, um item em risco de ruptura) e me diga se batem.
Não altere nenhuma análise ainda: só me diga o que os dados reais mostram de diferente do que a demo assume.
```
**Pronto quando:** relatório da loja gerado, números conferidos, lista do que a loja tem de diferente
(custo desatualizado? sem hora? devoluções misturadas nas vendas? códigos repetidos?).

Depois, para cada problema que apareceu:
```
Com base no que vimos nos dados da loja NOME, ajuste o importador e/ou a análise X para lidar com [problema].
Escreva primeiro um teste que reproduz o problema com um exemplo pequeno, depois a correção. Rode todos os testes.
```

---

## Etapa 2 — Ajudante de mapeamento de colunas

```
Crie o comando `python -m dashnator mapear --vendas arq --estoque arq --out mapeamento.json` que lê só o
cabeçalho e as primeiras linhas, sugere a coluna de cada campo canônico por nome parecido (ex.: "Vl Unit",
"Valor unitário", "Preço" → preco_unitario), pergunta no terminal o que ficou em dúvida e salva o JSON.
Nunca imprimir valores de colunas que pareçam dados pessoais. Com testes.
```
**Pronto quando:** você mapeia uma planilha nova em menos de 2 minutos sem editar JSON na mão.

---

## Etapa 3 — Aplicação web mínima (só depois de validar com uma loja)

```
Leia docs/BRIEF.md seções 6 e 8. Crie a v1 da aplicação web em dashnator/web/ com FastAPI + SQLite:
- cadastro e login simples (e-mail e senha com hash seguro), uma loja por conta;
- tela de upload de vendas, estoque e (opcional) orçamentos, usando o importador e o mapeamento salvo da loja;
- cada upload cria uma "versão dos dados" (guardar a data, o hash do arquivo e as tabelas já canônicas);
- uma página que mostra o mesmo conteúdo do relatório HTML atual para a versão mais recente.
Reaproveite o código existente em analyses/, pipeline.py e report/html.py sem duplicar. Sem JavaScript pesado:
HTMX no máximo. Testes para upload, isolamento entre lojas (uma loja nunca vê dados de outra) e login.
Pare e me mostre o plano de arquivos antes de escrever o código.
```
**Pronto quando:** você sobe os arquivos de uma loja pela tela e vê o painel; duas contas diferentes não se enxergam.

---

## Etapa 4 — Telas do painel

```
Divida o painel nas telas do brief (seção 6): Visão geral, Estoque, Curva ABC, Vendas (dia×hora e vendedores),
Vendas perdidas e orçamentos, Configurações. Gráficos com Chart.js servido localmente (sem CDN). Tudo
responsivo, pensado para o celular do dono no balcão. Na tela Estoque, a lista de compra sugerida precisa
poder ser exportada em Excel (agrupada por fornecedor) — um botão. Mantenha as cores e a linguagem do
relatório atual.
```

---

## Etapa 5 — Camada de IA (LLM) com verificação e cache

```
Leia CLAUDE.md (regras 1 e 5) e docs/BRIEF.md seção 7. Implemente em dashnator/ai/llm.py:
- chamada à API da Anthropic usando um modelo pequeno configurável por variável de ambiente (ANTHROPIC_API_KEY
  e DASHNATOR_MODELO), com o prompt do brief e o payload de ai/payload.py como ÚNICA entrada;
- saída em JSON no mesmo formato de template_insights.gerar();
- verificação com ai/verify.py; se falhar, tentar de novo UMA vez; se falhar de novo, usar o texto por regras;
- cache por (hash dos dados + hash da configuração): a mesma versão dos dados nunca gera uma segunda chamada;
- registrar tokens e custo estimado por chamada.
Testes com um cliente falso (sem chamar a API): resposta válida, resposta com número inventado, resposta
com JSON quebrado, cache funcionando. Mostre-me o prompt final antes de rodar com a API de verdade.
```
**Pronto quando:** abrir o painel 10 vezes gera 0 chamadas novas; um número inventado nunca aparece na tela.

---

## Etapa 6 — Registro de vendas perdidas no balcão

```
Crie uma tela mobile muito rápida (máximo 3 toques) para o balcão registrar uma venda perdida: busca do item
por código ou descrição, quantidade, motivo (sem estoque, sem aplicação cadastrada, preço, devolução ou troca
por incompatibilidade, outro). Salvar com data e hora. Esses registros alimentam a análise de vendas perdidas
que já existe. Para devolução por incompatibilidade, perguntar de qual fornecedor era a peça. Testes.
```
**Pronto quando:** um vendedor registra uma perda em menos de 15 segundos.

---

## Etapa 7 — Diagnóstico em PDF e lista de compra

```
Gere o PDF do diagnóstico a partir do HTML do relatório (Chrome headless ou outra opção já instalada; me diga
qual escolheu e por quê), com capa (nome da loja, período, data) e rodapé com a metodologia. Adicione a
exportação da lista de compra em Excel (openpyxl): uma aba por fornecedor, com item, estoque, venda por dia,
quantidade sugerida e custo. Testes de que os arquivos abrem e os totais batem com o relatório.
```

---

## Etapa 8 — Sazonalidade (só com 12 meses de histórico)

```
Implemente analyses/sazonal.py: índice sazonal por categoria e por mês, calculado só quando o histórico tem
pelo menos 365 dias (niches/autopecas.yaml: min_historico_sazonal_dias). Use-o para ajustar a venda diária
projetada na sugestão de compra de itens/categorias com sazonalidade marcante (ex.: bateria, ar-condicionado,
lona de freio em períodos de chuva), sem mudar as fórmulas do CLAUDE.md para quem não tem histórico.
Documente a fórmula no CLAUDE.md e escreva testes com um caso de resposta conhecida.
```

---

## Etapa 9 — Configurações e "sempre mantenho"

```
Tela de configuração por loja: janela de venda, cortes da curva ABC, dias para considerar encalhado, margem de
segurança, prazo por fornecedor e a lista de itens "sempre mantenho" (marcar por busca ou subir uma lista).
Salvar por loja; os padrões continuam vindo do niches/autopecas.yaml. Mudar a configuração invalida o cache
da IA (o hash da configuração muda). Testes.
```

---

## Etapa 10 — Colocar no ar com segurança

```
Prepare a publicação: Dockerfile, variáveis de ambiente, backup diário do SQLite e dos arquivos enviados,
HTTPS, limite de tamanho de upload, e uma página de termos de uso e política de privacidade em linguagem
simples (não coletamos dados pessoais de clientes da loja; o dono pode apagar tudo a qualquer momento — fazer o
botão "apagar meus dados" funcionar de verdade). Liste os riscos que sobraram em ordem de gravidade.
```
> Os textos legais (termos/privacidade) devem ser revisados por um advogado antes de cobrar de alguém.

---

## Etapa 11 — Só se o dono confirmar que é dor real: contas a receber

```
Leia docs/BRIEF.md seção 2 (v1.5). Implemente o aging de contas a receber para oficinas: faixas 1–15, 16–30,
31–60, 61–90 e 90+ dias por cliente (cliente identificado por código interno, nunca por nome ou CPF), com
sugestão de limite de crédito. Exige um novo arquivo canônico "titulos". Testes de resposta conhecida.
```

---

## Prompts úteis a qualquer momento

- **Auditar números:** `Escolha 5 números do relatório da loja NOME e recalcule cada um direto dos arquivos, sem usar o código do projeto. Mostre a conta e se bate.`
- **Revisar antes de entregar:** `Rode os testes, gere a demo e o relatório da loja NOME, abra o HTML em tela de celular (390px) e em desktop e liste qualquer texto cortado, número estranho ou termo que um dono de autopeças não entenderia.`
- **Novo nicho:** `Crie niches/<nicho>.yaml a partir do autopecas.yaml e um gerador de demo equivalente. Não altere as análises; se precisar, me diga por quê antes.`
