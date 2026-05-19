# PRD - Sistema de Gestão Jurídica "Quiet Luxury"

## Original Problem Statement
Redesign visual completo de sistema de gestão jurídica preservando funcionalidades legadas e aprimorando o módulo financeiro. Estética **Quiet Luxury** com paleta:
- Background: `#121212`
- Accent (gold): `#D4AF37`
- Text: `#F5F5F5`

## Requisitos do Produto
1. Calendar (Agenda) estilo Google Calendar — preservar estrutura.
2. UI/UX moderno, premium, glassmorphism com paleta acima.
3. Módulo Financeiro funcional (admin edita, advogado read-only) com tabelas e gráficos.
4. RBAC (controle de acesso por papel).
5. Drive de documentos com pastas hierárquicas e visualizador embutido.
6. Gestão de Processos estilo Kanban com drag-and-drop.

## Stack
- Backend: FastAPI + MongoDB + JWT
- Frontend: React + Tailwind + Framer Motion + dnd-kit + Recharts
- Idioma do usuário: **Português** (responder sempre em PT-BR)

## Implementado
| Data | Item |
|------|------|
| sessão anterior | Auth JWT (login/register/me) |
| sessão anterior | Modelos backend e endpoints (`server.py`) |
| sessão anterior | Tema "Quiet Luxury" (theme.js / theme-premium.js) |
| sessão anterior | Kanban com dnd-kit (`Processos.js`) |
| sessão anterior | Agenda estilo Google (`Agenda.js`) |
| sessão anterior | FinanceiroPremium com KPI cards, charts, RBAC |
| sessão anterior | Drive com pastas hierárquicas (expandir/colapsar) |
| 30/04/2026 | **Drive validado**: pastas com docs aninhados + visualizador embutido (PDF/imagem inline) funcionando |
| 04/05/2026 | **Agenda editável**: clique em compromisso → modal com detalhes do cliente + botões Editar/Excluir (PUT/DELETE no backend) |
| 04/05/2026 | **Financeiro zerado**: dados mockados de invoices/expenses/trust_accounts/time_entries removidos; analytics agora deriva 100% de `financial_records` (KPIs + gráficos coerentes com a tabela editável) |
| 19/05/2026 | **Audiências na Agenda**: novo tipo "hearing" com campos `process_number` e `court` (Órgão Julgador), cor dourada distintiva, exibido no modal de detalhes com botões Editar/Excluir |

## Endpoints-chave
- `POST /api/auth/login`, `GET /api/auth/me`
- `GET/POST /api/folders`, `DELETE /api/folders/:id`
- `GET/POST /api/documents/upload`, `DELETE /api/documents/:id`
- `GET/POST /api/appointments`
- `GET/PUT /api/processes`
- `GET /api/finance/analytics`

## Modelos de Dados
- `users`: id, email, hashed_password, name, role
- `appointments`: id, title, client_name, date, time, type, status
- `processes`: id, client_name, number, type, status, lawyer_id, updates
- `folders`: id, name, type, reference_id
- `documents`: id, folder_id, filename, file_type, file_data (base64)
- `invoices`, `trust_accounts` (financeiro)

## Backlog Priorizado

### P0 — concluído
- [x] Validar Drive.js (pastas hierárquicas + visualizador) ✅ 30/04/2026

### P1
- [ ] Refatorar componentes grandes:
  - `FinanceiroPremium.js` (581 linhas): extrair `CARD_ANIMATION` e `contentStyle` para constantes/`useMemo`, dividir em subcomponentes
  - `Drive.js` (425 linhas), `Agenda.js` (547 linhas)
  - `server.py`: quebrar `get_dashboard_analytics` e `seed_financial_data`

### P2
- [ ] Notificações direcionadas / Update Feed (advogado recebe push quando há mudança em processo dele)
- [ ] Melhorias de performance React (re-renders desnecessários)

## Credenciais de Teste
- admin@legal.com / admin123 (admin)

## Arquivos-Chave
- `/app/backend/server.py`
- `/app/frontend/src/pages/{Drive,FinanceiroPremium,Agenda,Processos,Dashboard}.js`
- `/app/frontend/src/theme.js`, `theme-premium.js`
- `/app/frontend/src/components/premium/*` (KPICard, AnimatedNumber, PremiumTable, StatusBadge)
