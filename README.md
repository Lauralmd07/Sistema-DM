# Sistema DM

Sistema jurídico para gestão de usuários, processos, agenda, documentos e financeiro.

## Autenticação

O sistema suporta:

- Login tradicional por e-mail e senha.
- Cadastro de novos usuários.
- Login com Google usando Google Identity Services.
- Sessão por cookies HTTP-only com JWT.
- Vinculação automática de uma conta Google a um usuário existente pelo mesmo e-mail verificado.

## Configuração do Google

1. Crie ou selecione um projeto no Google Cloud Console.
2. Configure a tela de consentimento OAuth.
3. Crie um cliente OAuth do tipo **Aplicativo da Web**.
4. No frontend, configure `REACT_APP_GOOGLE_CLIENT_ID` com o Client ID.
5. No backend, configure `GOOGLE_CLIENT_ID` com o mesmo Client ID.
6. Adicione o domínio do frontend aos **Authorized JavaScript origins**. Em produção, use `https://lauralmd07.github.io`.
7. Para desenvolvimento local, adicione `http://localhost:3000`.

O fluxo implementado usa o ID token do Google e o backend valida assinatura, audiência e e-mail verificado antes de criar a sessão.

## Variáveis de ambiente

Veja `frontend/.env.example` e `backend/.env.example`.

Nunca coloque `GOOGLE_CLIENT_SECRET`, `MONGO_URL` ou `JWT_SECRET` no frontend ou no repositório. O fluxo atual de login usa apenas o Client ID público no navegador; a validação da identidade ocorre no backend.

## Deploy

### Frontend

Configure no ambiente de build:

```text
REACT_APP_API_URL=https://sistema-dm.onrender.com/api
REACT_APP_GOOGLE_CLIENT_ID=<seu-client-id>
```

### Backend / Render

Configure:

```text
MONGO_URL=<sua-connection-string>
DB_NAME=legal_system
JWT_SECRET=<segredo-aleatório-forte>
FRONTEND_URL=https://lauralmd07.github.io/Sistema-DM
GOOGLE_CLIENT_ID=<seu-client-id>
```

Não compartilhe os valores reais dessas variáveis.
