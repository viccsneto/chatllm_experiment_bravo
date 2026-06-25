# Strategic Blueprint

> Focus on the **what** and **why**. The code will follow.

**Hard rule**: AI agents must not edit this file and must not draft paste-ready content for it.

## The Problem
Quero que o usuário possa criar e alternar sessões através de uma barra lateral (similar a ChatGPT e Gemini), cada usuário terá acesso somente a sua própria sessão; cada sessão guarda seu histórico, se a sessão não tiver título, o título deve ser definido automaticamente com base no contexto (possível já na primeira resposta do modelo).

## Steps
- Criar um modelo relacional, uma tabela ChatSession com chave estrangeira nas mensagens (ChatMessage) (Relacional, título na sessão, query simples, ordering por data)
- Quando a sessão for criada e a primeira resposta chegar, o modelo deve gerar um título baseado na primeira mensagem.
    Ex de fluxo: 1 - Usuário cria sessão → título = null
                2 - Sidebar mostra a sessão como "Nova conversa"
                3 - Usuário envia primeira mensagem
                4 - Modelo responde (streaming normal)
                5 - APÓS a resposta, você chama o OpenRouter com:
                     "Crie um título curto (máx 6 palavras) para esta conversa: 
                      {primeira mensagem do usuário} → {resposta do modelo}"
                6 - Salva o título gerado na sessão
- Quero que os usuários acessem apenas as suas próprias sessões: toda sessão pertence a um usuário, e todas as queries filtram por ele.
- Quero que haja uma barra lateral (similar a ChatGPT e Gemini) para que cada usuário possa criar e alternar sessões.
- Quero que em cada sessão tenha o histórico.
- Criar Endpoints: POST/api/sessions (criar nova sessão) e GET/api/sessions (listar sessões do usuário), GET/api/sessions/{id}/messages (carregar histórico)

## Success Looks Like
- Mostrar uma barra lateral com sessões, seja possível alternar entre elas, cada usuário tenha acesso apenas às suas sessões (endpoints retornam 200 com sessões do usuário logado), cada sessão tem o histórico de mensagens (ao clicar numa sessão o histórico carrega), título é gerado automaticamente após a primeira resposta.
## Notes
- 

---
**⚠️ HUMAN ONLY**: This file is your strategic space. AI agents must not edit it.
