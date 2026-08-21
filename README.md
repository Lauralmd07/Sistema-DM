# Sistema DM

Sistema jurídico para gestão de advogados, com agenda, processos, clientes, documentos e financeiro.

## Estrutura

- `frontend/` — React + React Router + Tailwind + Axios.
- `backend/` — FastAPI + MongoDB + JWT + Google Identity Services.

## Variáveis do backend

Configure no Render ou no ambiente local:

- `MONGO_URL`
- `DB_NAME` (opcional; padrão `legal_system`)
- `JWT_SECRET`
- `FRONTEND_URL`
- `GOOGLE_CLIENT_ID`
- `ADMIN_NAME` (opcional)
- `ADMIN_EMAIL`
- `ADMIN_PASSWORD`

O administrador é criado automaticamente na inicialização quando `ADMIN_EMAIL` e `ADMIN_PASSWORD` estão configurados. O cadastro público nunca pode escolher a função `admin`.

## Variáveis do frontend

- `REACT_APP_API_URL`
- `REACT_APP_GOOGLE_CLIENT_ID`

## Desenvolvimento

Backend:

```bash
cd backend
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Frontend:

```bash
cd frontend
npm install
npm start
```

## Produção

O frontend está preparado para GitHub Pages e o backend para Render. O workflow de CI valida a compilação do backend e do frontend; o workflow de Pages publica a branch `conflict_190526_1511`.

## Autenticação

O sistema mantém login por e-mail/senha e login com Google. A autenticação usa cookies HTTP-only, com refresh automático do access token no frontend.

Nunca versione `.env`, senhas, chaves privadas ou credenciais do Google/MongoDB.
