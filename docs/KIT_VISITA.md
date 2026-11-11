# Kit de visita — levar o Dashnator às autopeças da sua região

Objetivo da primeira visita: **sair com os arquivos de vendas e estoque da loja** (ou com a data marcada para
recebê-los) e com a resposta do dono sobre qual dor pesa mais. Não é vender; é entregar um diagnóstico
grátis em poucos dias e ver se o dono reconhece os números.

## O que levar
- Celular com `demo.html` aberto (e uma cópia offline no notebook). Mostre em 3 minutos.
- Um diagnóstico impresso da demo (use "Imprimir / salvar PDF") para deixar na mão do dono.
- Caderno para anotar as respostas literais. As frases do dono valem mais que a sua interpretação.

## Abertura (30 segundos)
> "Eu estou montando uma ferramenta que olha as vendas e o estoque da loja e mostra três coisas: quanto
> dinheiro está parado em peça que não gira, quais peças de saída vão faltar antes do pedido chegar, e o que
> o balcão deixou de vender. Eu faço um diagnóstico da sua loja de graça, com os dados que o seu sistema já
> exporta. Posso mostrar em 3 minutos como fica?"

Mostre a demo no celular. Diga que os dados são fictícios. Deixe o dono mexer.

## Perguntas de descoberta (anote as respostas)
1. "Dessas seis situações, qual é a que mais pesa hoje? Ordene as três primeiras."
   - dinheiro parado em estoque e peça que falta quando o cliente pede;
   - vender a peça errada (aplicação, devolução, troca);
   - cliente comparando preço com internet/marketplace e a margem apertando;
   - equipe de balcão: treinar, rotatividade, quem vende mais e quem vende menos;
   - imposto/nota fiscal (substituição tributária, mudanças da reforma);
   - prazo do fornecedor e capital de giro.
2. "Como vocês decidem hoje o que comprar e quando? Quem decide?"
3. "Quando falta uma peça que o cliente pede, vocês anotam em algum lugar?"
4. "Quando o cliente pede orçamento e não fecha, isso fica registrado no sistema?"
5. "Qual sistema (ERP) vocês usam? Ele exporta relatório para Excel?"
6. "O custo das peças no cadastro está atualizado?"
7. "Se isso mostrasse R$ X de dinheiro parado e R$ Y de venda em risco, o que você faria com a informação?"
8. (No fim, sem pressão) "Se fosse útil todo mês, quanto você acharia justo pagar?"

> Não cite preço na primeira visita. A pergunta 8 serve para ouvir a faixa que ele imagina.

## O que pedir
Peça ao dono ou a quem opera o sistema para **exportar em Excel/CSV**:
1. **Vendas dos últimos 12 meses**, uma linha por item vendido, com: data e hora, número do pedido/nota,
   código do produto, descrição, quantidade, preço unitário de venda e, se o sistema tiver, custo unitário,
   categoria/grupo, marca e vendedor.
2. **Posição de estoque de hoje**, com: código, descrição, quantidade, custo unitário, preço de venda e,
   se tiver, categoria, marca e fornecedor.
3. (Opcional, se o sistema guarda) **Orçamentos/pré-vendas** dos últimos 12 meses com indicação de quais viraram venda.

**Sem dados pessoais de clientes.** Se o relatório vier com nome, CPF/CNPJ, telefone ou e-mail, tudo bem: o
importador descarta essas colunas automaticamente. Mesmo assim, diga ao dono que não precisa enviar essas colunas.

Se ele não souber qual relatório usar, não insista no nome técnico: peça para quem opera o sistema abrir
com você o menu de relatórios e procurar "vendas por produto/item" e "posição de estoque". Anote o nome do
sistema e do relatório que funcionou, isso vale ouro para as próximas lojas.

## Compromisso que você assume (diga em voz alta e mande por escrito)
> "Vou usar os arquivos apenas para montar o diagnóstico da sua loja. Não vou mostrar nem compartilhar os seus
> números com ninguém, nem com outras lojas. Quando você quiser, eu apago todos os arquivos."

Cumpra isso à risca: guarde os arquivos só em `dados_reais/` (fora do Git), apague quando a loja pedir.
Antes de cobrar de alguém, peça a um advogado para revisar um termo de confidencialidade e uso de dados.

## Depois da visita (até 3 dias)
1. Rode `python -m dashnator report ...` (ou use o prompt da Etapa 1 do roteiro) e **confira 3 números** direto dos arquivos.
2. Gere o PDF. Escolha as **3 recomendações com mais dinheiro** e escreva no topo, em linguagem de balcão.
3. Marque 20 minutos para entregar pessoalmente. Mostre no celular dele, com os itens da loja dele.

## Na entrega do diagnóstico
Perguntas para fazer, nesta ordem, e anotar:
- "Esses números parecem certos para você?" (se não, pergunte qual está errado e por quê)
- "Algum item aí te surpreendeu?"
- "O que você vai fazer com isso esta semana?" (anote a ação; é o sinal mais forte)
- "Posso voltar daqui a um mês com os dados novos para ver o que mudou?"
- "Se eu te mandasse isso todo mês, valeria quanto para você?"

**Sinais de que deu certo:** o dono reconhece os números, age em pelo menos 1 recomendação e aceita ver de novo
no mês seguinte. **Sinais de alerta:** "legal, mas..." sem ação; números que ele não reconhece e não quer
investigar; só pergunta de preço sem olhar os itens.

## Mensagem para marcar a visita (mande você mesmo, do seu WhatsApp)
> "Oi, [nome], aqui é o Lustoza. Estou montando uma ferramenta que mostra para a autopeça quanto dinheiro está
> parado em estoque e quais peças vão faltar. Faço um diagnóstico da sua loja de graça. Posso passar aí
> [dia] para mostrar em 10 minutos? Não vendo nada nessa visita."

## Registro por loja (copie para cada visita)
```
Loja:                    Cidade/bairro:
Dono / contato:          Data da visita:
ERP usado:               Relatórios que exportam:
Dores (top 3 na ordem do dono):
Como decide compra hoje:
Registra venda perdida? orçamento?
Custo atualizado? sim / mais ou menos / não
Arquivos recebidos em:   Diagnóstico entregue em:
O dono reconheceu os números?    Ação que ele vai tomar:
Voltaria no mês que vem?         Faixa de preço que ele citou:
```
