# Configuração de acesso

Este arquivo não contém credenciais válidas.

## Administrador

A conta administrativa é criada pelo backend quando estas variáveis de ambiente estão configuradas:

- `ADMIN_NAME`
- `ADMIN_EMAIL`
- `ADMIN_PASSWORD`

A senha deve ter pelo menos 8 caracteres.

## Advogados

Novos cadastros públicos são criados automaticamente com a função `lawyer`. O cliente não consegue escolher `admin` pelo formulário de cadastro.

## Google

O login com Google exige `GOOGLE_CLIENT_ID` no backend e `REACT_APP_GOOGLE_CLIENT_ID` no frontend. O Client ID deve ser configurado no Google Cloud Console com a origem autorizada do frontend e os ambientes usados durante o desenvolvimento.

## Segurança

Nunca coloque `MONGO_URL`, `JWT_SECRET`, `ADMIN_PASSWORD`, credenciais do Google ou outras chaves privadas em arquivos versionados. Use as variáveis de ambiente do Render/GitHub Actions.
