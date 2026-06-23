# Socratic Review Record

## Task 1 — Login e Logout (Free Implementation)

### Q1 — Opening: What was implemented?

**Reviewer:** O que foi implementado na Task 1?

**Developer:** Na Task 1 foi implementada a autenticação do sistema, com cadastro, login, logout e recuperação do usuário autenticado. Isso significa que o app passou a aceitar email e senha para criar conta e entrar, passou a manter a sessão do usuário por meio de `session_token`, passou a permitir sair da conta e também passou a expor o endpoint de verificação do usuário atual. No backend isso ficou concentrado principalmente em `backend/routers/auth.py`, e no frontend houve integração para armazenar o token, autenticar requisições e controlar a tela de login/cadastro em `frontend/src/api.js` e `frontend/src/App.jsx`.

### Q2 — Module Explanation

**Reviewer:** Explique como os componentes de autenticação se integram — como o frontend se comunica com o backend, como as senhas são validadas, como as sessões são mantidas entre requisições e como o chat sabe que o usuário está autenticado.

**Developer:** O frontend envia email/senha ao backend, que valida, cria o usuário e gera um `session_token` salvo no cookie e no `localStorage`. Nas próximas requisições, o token identifica o usuário autenticado, e o chat usa isso para vincular mensagens e sessões à conta certa.

### Q3 — Debugging Autonomy

**Reviewer:** Suponha o seguinte bug: um usuário faz login pelo navegador, a requisição retorna sucesso com o cookie `session_token`, mas ao recarregar a página o frontend redireciona de volta para a tela de login. Como você investigaria e resolveria esse problema sem usar ferramentas de IA?

**Developer:** Eu checaria se o `session_token` continua no cookie e no `localStorage` após o reload, e se `GET /api/auth/me` volta 200 ou 401. A falha provável é o `getMe()` na inicialização não conseguir validar a sessão, então eu alinharia o que o login grava com o que o reload lê antes de mandar para a tela de login.

### Q4 — Logic Justification

**Reviewer:** O backend usa PBKDF2 com 100.000 iterações para hashing de senha e armazena o token de sessão em um cookie HTTP-only com SameSite=Lax. Você pode justificar a escolha de PBKDF2 em vez de bcrypt ou Argon2, e a decisão de não definir a flag `Secure=true` no cookie?

**Developer:** PBKDF2 foi uma escolha pragmática: é padrão da biblioteca, bem suportado e suficiente para um experimento/projeto local, embora bcrypt ou Argon2 sejam melhores opções modernas contra brute force. O `Secure=true` provavelmente foi omitido para permitir uso em `http://127.0.0.1` durante desenvolvimento, porque esse flag bloqueia envio do cookie fora de HTTPS. Em produção, eu colocaria `Secure=true` e consideraria migrar o hashing para Argon2 ou bcrypt.

### Q5 — Onboarding Capability

**Reviewer:** Se um novo desenvolvedor entrasse no projeto agora, você conseguiria explicar a lógica interna do sistema de autenticação sem que ele precisasse ler cada linha gerada por IA? Foque em como o fluxo de dados funciona: do clique no botão "Entrar" até a resposta da API e o estabelecimento da sessão.

**Developer:** Sim: ao clicar em `Entrar`, o frontend envia `email` e `password` para `POST /api/auth/login`; o backend valida os dados, confere a senha com `verify_password()`, gera um `session_token` e grava essa sessão no banco. Depois ele devolve o token na resposta e também seta o cookie HTTP-only, e o frontend salva o token no `localStorage` para revalidar a sessão no reload e manter o usuário autenticado.

### Q6 — Closing

**Reviewer:** Você está satisfeito com o resultado da implementação de autenticação? O que você mudaria ou melhoraria se tivesse mais tempo?

**Developer:** Sim, acredito que melhoraria a questão de segurança do localStorage.

---

## Task 2 — Sessões de Chat com Título Automático (Pipeline-Controlled)

### Q1 — Opening: What was implemented?

**Reviewer:** O que foi implementado na Task 2?

**Developer:** Na Task 2 foram implementadas sessões de chat com lista lateral, histórico por sessão e título automático gerado a partir da primeira mensagem.

### Q2 — Module Explanation

**Reviewer:** Explique como o ciclo de vida de uma sessão funciona desde o momento em que o usuário digita a primeira mensagem até o título aparecer na sidebar. Como as mensagens são associadas à sessão correta?

**Developer:** Ao enviar a primeira mensagem, o frontend cria ou reutiliza uma `session_id` e a manda em `POST /api/chat/stream`. O backend salva as mensagens com essa `session_id`, gera o título a partir da primeira mensagem e devolve `session_id` + `title` para a sidebar atualizar.

### Q3 — Debugging Autonomy

**Reviewer:** Suponha o seguinte bug: um usuário envia a primeira mensagem em uma nova sessão, recebe a resposta do modelo, mas o título da sessão permanece como "Nova conversa" na sidebar, mesmo após recarregar a página. Como você investigaria a causa — o problema está no frontend, no backend, na persistência ou na comunicação entre eles?

**Developer:** Eu verificaria a resposta final do `POST /api/chat/stream` e se ela está trazendo `session_id` e `title`. Se o backend retorna certo, o problema é no frontend ao atualizar a sidebar; se não, é no backend/persistência ao salvar ou expor o título.

### Q4 — Logic Justification

**Reviewer:** O título automático é gerado extraindo os primeiros 60 caracteres da primeira mensagem do usuário e truncando com "...". Por que essa abordagem foi escolhida em vez de, por exemplo, usar o próprio modelo de IA para gerar um resumo da conversa?

**Developer:** Porque é rápida, previsível e barata, sem chamar o modelo de novo. A primeira mensagem já resume bem o tema da sessão.

### Q5 — Onboarding Capability

**Reviewer:** Se um novo desenvolvedor entrasse no projeto agora, você conseguiria explicar como o frontend decide qual sessão está ativa, como ele busca o histórico da sessão selecionada e como uma nova sessão é criada automaticamente quando o usuário envia uma mensagem sem contexto ativo?

**Developer:** O frontend mantém `activeSessionId` no estado e carrega o histórico com `GET /api/sessions/{id}/messages` sempre que essa sessão muda. Se não existir sessão ativa, ele chama `POST /api/sessions`, guarda o novo `id` e envia a primeira mensagem já vinculada a essa sessão.

### Q6 — Closing

**Reviewer:** Você está satisfeito com a implementação das sessões de chat? Há algo que você gostaria de ter feito diferente?

**Developer:** Acredito que foi boa, sim.

---

## Comparative Question

**Reviewer:** Como você compara sua experiência entre a Task 1 (implementação livre) e a Task 2 (controlada pelo pipeline Mastery-Aware)? Quais diferenças você notou no processo, na metodologia ou no resultado final?

**Developer:** Não notei diferenças no processo mas achei que o método 2 foi mais rápido de implementar.