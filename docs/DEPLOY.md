# Colocar o Dashnator (Streamlit) no ar

O painel é um app Streamlit: `streamlit_app.py` na raiz, que usa o pacote `dashnator/`.

## Rodar no seu computador
```bash
python -m venv .venv
.venv\Scripts\activate            # no Linux/Mac: source .venv/bin/activate
pip install -r requirements.txt
streamlit run streamlit_app.py --server.address localhost
```
Abre em http://localhost:8501. Login da apresentação: usuário `teste`, senha `teste`.
`--server.address localhost` faz o app aceitar só o seu computador; sem isso, o Streamlit aceita
qualquer máquina da rede.

## Recomendado para a primeira apresentação: Streamlit Community Cloud
Gratuito, feito para Streamlit, publica direto de um repositório do GitHub e dá um endereço
`https://<nome>.streamlit.app`.

1. Coloque esta pasta num repositório do GitHub (só ela, não a pasta de cima). Pode ser privado.
   O `.gitignore` já deixa de fora `dados_reais/`, `saida/`, `.env` e `.streamlit/secrets.toml`.
2. Em share.streamlit.io, entre com a conta do GitHub e clique em **Create app**.
3. Escolha o repositório, o branch e o arquivo principal `streamlit_app.py`. Em **Advanced settings**,
   escolha Python 3.13.
4. Ainda em **Advanced settings > Secrets**, troque o login antes de mandar o link para alguém:
   ```toml
   DASHNATOR_USUARIO = "seu-usuario"
   DASHNATOR_SENHA = "uma-senha-de-verdade"
   ```
   Sem esses dois valores, o login continua `teste` / `teste`.
5. **Deploy**. A cada `git push`, o app se atualiza sozinho.

O que saber sobre esse serviço:
- O app "dorme" depois de alguns dias sem acesso e leva cerca de um minuto para acordar. Abra o link
  um pouco antes da apresentação.
- Com repositório público, o endereço do app é público: quem tiver o link chega na tela de login.
  Com repositório privado, dá para liberar o acesso só para e-mails convidados.
- Memória de cerca de 1 GB: sobra para a demonstração e para os arquivos de uma loja.

## Cuidado com dados reais de loja
Esta versão tem **um login só, igual para todos**: é uma porta para a apresentação, não a separação por
loja prevista na v1 (`docs/BRIEF.md`, seção 2). Enquanto for assim:
- use a demonstração nas apresentações;
- para rodar o diagnóstico de uma loja real, prefira o seu computador (`streamlit run` local ou
  `python -m dashnator report`), como no `docs/KIT_VISITA.md`;
- os arquivos enviados pelo painel ficam só na memória da sessão e somem ao fechar a aba; nada é gravado
  em disco, e colunas com CPF, CNPJ, telefone, e-mail ou nome de cliente são descartadas na leitura.

## Outras opções
| Onde | Quando faz sentido | Observação |
| --- | --- | --- |
| Hugging Face Spaces (SDK Streamlit ou Docker) | alternativa gratuita ao Community Cloud | mesmo esquema: repositório + segredos |
| Render, Railway ou Fly.io (com o `Dockerfile` desta pasta) | quando precisar de domínio próprio, app sempre ligado ou disco para guardar dados | pago a partir de poucos dólares por mês |
| Servidor próprio (VPS) com Docker | controle total, dados no Brasil | exige cuidar de HTTPS, atualização e backup |
| Vercel | **não serve** | o Streamlit precisa de um servidor sempre ligado com WebSocket; a Vercel roda funções que ligam e desligam |

Com Docker (não testado nesta máquina, que não tem Docker rodando):
```bash
docker build -t dashnator .
docker run -p 8501:8501 -e DASHNATOR_USUARIO=dono -e DASHNATOR_SENHA=troque dashnator
```

## Antes de cobrar de alguém (etapa 10 do roteiro)
Login por loja com senha guardada com hash, uma área de dados por loja, HTTPS com domínio próprio,
backup, botão "apagar meus dados" e os textos de termos e privacidade revisados por advogado.
