# Sistema de Gestão Jurídica - PRD

## Visão Geral
Sistema completo de gestão jurídica com design premium, controle de acesso baseado em funções e módulos integrados.

## Identidade Visual
- **Fundo Principal**: Preto Antracite (#121212)
- **Detalhes/Botões**: Dourado Metálico (#D4AF37)
- **Textos**: Branco Marfim (#F5F5F5)
- **Estilo**: Moderno, minimalista, bordas arredondadas, ícones elegantes

## Módulos

### A. Agenda de Consultas
- **Primeira Consulta (Lead)**: Nome, Telefone, Assunto
- **Retorno**: Nome, Telefone, CPF, RG, Endereço Completo
- **Visualização**: Calendário mensal e semanal com cores

### B. Gestão de Processos (Kanban)
- **Novos**: Número do Cliente, CPF, Tipo de Ação, Descrição
- **Em Andamento**: Linha do Tempo de Atualizações (data + descrição)
- **Finalizados**: Campo "Sentença do Juiz"

### C. Drive Jurídico
- Criação de pastas por cliente/processo
- Upload de arquivos (PDF, DOCX, Imagens)
- Visualização prévia no navegador

### D. Módulo Financeiro
- Controle de entradas (honorários) e saídas (custos)
- Gráficos de faturamento mensal
- Cálculo: Lucro = Receitas - Despesas

## Controle de Acesso

### Administrador
- Acesso total a todos os módulos
- Visualiza processos de todos os advogados
- Único com acesso ao módulo Financeiro completo

### Advogado
- Acesso: Agenda, Kanban, Drive
- Restrição: Apenas processos vinculados ao seu nome
- Financeiro: Apenas seus próprios honorários

## Stack Técnico
- **Frontend**: React.js com Tailwind CSS
- **Backend**: Python FastAPI
- **Banco de Dados**: MongoDB
- **Autenticação**: JWT com bcrypt
