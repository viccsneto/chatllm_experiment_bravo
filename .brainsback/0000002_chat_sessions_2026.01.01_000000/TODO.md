# Strategic Blueprint

> Focus on the **what** and **why**. The code will follow.

## The Problem
O sistema atual possui um fluxo de chat linear e volátil, onde o histórico de mensagens não é persistido de forma organizada por contexto. Precisamos implementar o conceito de "Sessões de Chat" (múltiplas conversas independentes), permitindo que o usuário crie, alterne e delete chats através de uma barra lateral (UI inspirada no ChatGPT/Gemini). Além disso, o sistema deve ser inteligente o suficiente para gerar títulos automáticos para essas sessões com base na primeira interação do usuário, melhorando a experiência de navegação sem exigir esforço manual.

## Steps
- [ ] **Banco de Dados (Model/Schema)**
  - [ ] Criar a tabela/entidade `ChatSession` (campos: `id`, `user_id`, `title`, `created_at`, `updated_at`).
  - [ ] Relacionar a tabela de mensagens (`ChatMessage`) com `ChatSession` através de uma chave estrangeira `session_id`.
  - [ ] Executar e validar as migrações no banco de dados.

- [ ] **Backend (API & Rotas)**
  - [ ] Criar endpoint `GET /api/sessions` para listar as sessões do usuário logado.
  - [ ] Criar endpoint `POST /api/sessions` para inicializar uma nova sessão.
  - [ ] Criar endpoint `DELETE /api/sessions/{id}` para encerrar/deletar uma sessão e suas mensagens atreladas.
  - [ ] Criar endpoint `PATCH /api/sessions/{id}/title` para atualizações manuais ou automáticas do título.
  - [ ] Atualizar o endpoint de envio de mensagem (`ChatRequest`) para aceitar e validar o parâmetro obrigatório `session_id`.

- [ ] **Inteligência Artificial (Título Automático)**
  - [ ] Criar uma função/serviço no backend para detectar se a sessão ainda está sem título (ex: "Nova Conversa").
  - [ ] Implementar chamada assíncrona ao LLM logo após a primeira resposta da sessão, enviando um prompt de resumo (ex: *"Resuma o assunto desta conversa em até 4 a 6 palavras, sem pontuação"*).
  - [ ] Atualizar o título da sessão no banco de dados com o retorno do modelo.

- [ ] **Frontend (Interface & Componentização)**
  - [ ] Desenvolver o componente `Sidebar.jsx` para listar as sessões de chat salvas e incluir um botão de "Novo Chat".
  - [ ] Implementar o estado global/contexto no frontend para gerenciar a `activeSessionId`.
  - [ ] Adaptar o container principal do chat para buscar o histórico da sessão ativa toda vez que o usuário alternar de chat na Sidebar.
  - [ ] Garantir que o envio de novas mensagens envie o `session_id` correto no payload da requisição.

- [ ] **Testes & Validação**
  - [ ] Criar testes de integração para as rotas da API de sessões.
  - [ ] Validar o comportamento de concorrência (garantir que as mensagens de uma sessão não vazem para outra).
  - [ ] Testar o tempo de resposta da geração do título automático para garantir que não bloqueie o fluxo principal do chat.

## Success Looks Like
- [ ] O usuário consegue criar múltiplos chats isolados e alternar entre eles pela barra lateral.
- [ ] Ao atualizar a página, o histórico de cada sessão é renderizado corretamente com base no banco de dados.
- [ ] A exclusão de uma sessão remove o chat da barra lateral e limpa os registros correspondentes.
- [ ] Após enviar a primeira mensagem e receber a resposta, o título do chat muda dinamicamente de "Nova Conversa" para um resumo inteligente do contexto.

## Notes
- [ ] **Performance do Título Automático:** A chamada ao LLM para gerar o título deve ser feita em background (assíncrona) ou logo após o stream da primeira resposta terminar, evitando travar a experiência do usuário.
- [ ] **Casos de Borda:** Se o usuário deletar a sessão ativa no momento, o frontend deve redirecionar automaticamente para a sessão mais recente ou criar uma nova sessão em branco.
- [ ] **Limitação de Tokens:** O prompt de geração de título só precisa analisar o primeiro par de `[User Prompt / AI Response]` para economizar contexto e tokens.