# Strategic Blueprint

> Focus on the **what** and **why**. The code will follow.

**Hard rule**: AI agents must not edit this file and must not draft paste-ready content for it.

## The Problem
Implementar um sistema de persistência de chat onde cada sessão é vinculada exclusivamente ao usuário autenticado. O objetivo é permitir que o usuário gerencie seu histórico e identifique conversas rapidamente através de títulos gerados automaticamente, evitando a sobrecarga cognitiva de lidar com múltiplos chats sem nomes.

## Steps
- [ ] Modelar o banco de dados para associar chats e mensagens ao user_id da Tabela de Usuários.
- [ ] Criar o endpoint de criação de sessão que salva o histórico inicial.
- [ ] Implementar a lógica que extrai um título a partir da primeira interação (via LLM) e atualiza o registro do chat.
- [ ] Implementar o endpoint de listagem que retorna apenas os chats pertencentes ao usuário logado.

## Success Looks Like
- [ ] O sistema retorna 200 OK apenas com os chats do user_id atual, garantindo isolamento total de dados.
- [ ] A primeira interação do usuário dispara automaticamente a geração e o salvamento do título no banco.
- [ ] O frontend exibe a lista de chats com títulos legíveis, carregados corretamente do backend.

## Notes
- [ ] O título deve ser gerado apenas uma vez no inicio da conversa com o chat

---
**⚠️ HUMAN ONLY**: This file is your strategic space. AI agents must not edit it.
