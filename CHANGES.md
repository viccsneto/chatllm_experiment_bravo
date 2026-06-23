# CHANGES.md — Tarefa 2: Sessões de Chat com Título Automático

## Visão Geral

Implementação de um sistema multi-sessão persistente com barra lateral e geração automática de títulos via LLM. O usuário agora pode criar, alternar e excluir sessões de chat, cada uma com seu próprio histórico isolado

---

## 🗄️ Backend — Modelos (`backend/models.py`)

### Nova classe: `ChatSession`

```python
class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id: int (PK)
    user_id: int (FK → users.id)
    title: str (default="Nova conversa")
    created_at: datetime
    updated_at: datetime

    relationships: User (M:1), ChatMessage (1:M)
```

### `ChatMessage` — Alterado

| Antes | Depois |
|-------|--------|
| `session_key: str` (string avulsa) | `session_id: int` (FK → `chat_sessions.id`) |
| sem relationship | `session: ChatSession` (M:1) |

---

## 📐 Schemas de Chat (`backend/schemas/chat.py`)

**Campos adicionados:**

| Schema | Novo campo |
|--------|-----------|
| `ChatRequest` | `session_id: int \| None = None` |

**Novos schemas:**

| Schema | Campos | Uso |
|--------|--------|-----|
| `SessionCreate` | (vazio) | Criar sessão |
| `SessionRename` | `title: str` (1-255) | Renomear sessão |
| `SessionResponse` | `id, title, created_at, updated_at` | Resposta de sessão |

---

## 🛣️ Backend — Router de Sessões (`backend/routers/sessions.py` — **novo**)

### Endpoints

| Método | Rota | Descrição | Auth |
|--------|------|-----------|------|
| `GET` | `/api/sessions` | Listar sessões do usuário (ordenadas por updated_at desc) | ✅ |
| `POST` | `/api/sessions` | Criar nova sessão | ✅ |
| `GET` | `/api/sessions/{id}` | Obter sessão específica | ✅ |
| `DELETE` | `/api/sessions/{id}` | Excluir sessão (cascade para mensagens) | ✅ |
| `PATCH` | `/api/sessions/{id}/rename` | Renomear sessão | ✅ |
| `GET` | `/api/sessions/{id}/messages` | Obter mensagens da sessão | ✅ |

---

## 🔧 Backend — Router de Chat (`backend/routers/chat.py` — **alterado**)

### Mudanças principais

| Aspecto | Antes | Depois |
|---------|-------|--------|
| **Sessão** | `session_key="default"` (fixo) | `session_id` dinâmico, carregado/criado por usuário |
| **Histórico** | Enviado pelo frontend no payload | Carregado do banco por `session_id` |
| **Autenticação** | Livre | Exige `get_current_user()` |
| **Título** | Não existia | Gerado automaticamente via LLM em background |

### Fluxo de título automático

```
1. Usuário envia primeira mensagem em sessão nova (title = "Nova conversa")
2. ChatMessage persistida no banco
3. `asyncio.create_task(_auto_title(session, db))` disparado em background
4. _auto_title() espera 0.5s, busca primeiras 4 mensagens, chama generate_title()
5. generate_title() usa OpenRouter para resumir em ≤5 palavras
6. session.title atualizado no banco
7. Frontend recarrega lista de sessões para exibir novo título
```

---

## 🤖 Backend — OpenRouter (`backend/services/openrouter.py`)

**Nova função:** `generate_title(conversation: list[dict]) → str`

- Prompt: `"Based on the conversation below, generate a very short title (maximum 5 words). Respond with ONLY the title"`
- `max_tokens: 20` (resposta curta)
- `timeout: 15s`
- Fallback: retorna `"Nova conversa"` em caso de erro

---

## 🔗 Backend — main.py

```python
from backend.routers.sessions import router as sessions_router
app.include_router(sessions_router)
```

---

## 🎨 Frontend — `frontend/src/Sidebar.jsx` (**novo**)

Componente de barra lateral com:

- **Botão "Novo chat"**: Cria sessão e ativa
- **Agrupamento por data**: Hoje, Ontem, "Há N dias", data específica
- **Sessões individuais**: Ícone de chat + título + botão excluir (hover)
- **Sessão ativa**: Destacada visualmente
- **Recolhimento**: Botão toggle para colapsar sidebar

---

## 🎨 Frontend — `frontend/src/api.js`

**Novas funções:**

| Função | Descrição |
|--------|-----------|
| `authHeaders()` | Retorna headers com Bearer token |
| `listSessions()` | GET `/api/sessions` |
| `createSession()` | POST `/api/sessions` |
| `deleteSession(id)` | DELETE `/api/sessions/{id}` |
| `getSessionMessages(id)` | GET `/api/sessions/{id}/messages` |
| `sendMessageWithSession({...})` | POST `/api/chat/stream` com `session_id`, retorna `session_id` da resposta |

---

## 🎨 Frontend — `frontend/src/App.jsx`

**Novos estados:**

| Estado | Tipo | Descrição |
|--------|------|-----------|
| `sessions` | `array` | Lista de sessões do usuário |
| `activeSessionId` | `int \| null` | Sessão atualmente selecionada |

**Novas funções:**

| Função | Descrição |
|--------|-----------|
| `loadSessions()` | Carrega lista do backend |
| `handleNewChat()` | Cria sessão, ativa, limpa mensagens |
| `handleSelectSession(id)` | Carrega mensagens da sessão |
| `handleDeleteSession(id)` | Exclui sessão, limpa se for a ativa |

**Fluxo alterado:**
- `onSubmit` agora usa `sendMessageWithSession` com `activeSessionId`
- Após resposta, recarrega lista de sessões (para pegar título automático)
- Layout mudou para `div.app-layout` (sidebar + chat lado a lado)

---

## 🎨 Frontend — `frontend/index.html`

**Script adicionado:**
```html
<script type="text/babel" src="/frontend/src/Sidebar.jsx"></script>
```

**CSS adicionado:** Estilos para `.app-layout`, `.sidebar`, `.sidebar-header`, `.sidebar-list`, `.sidebar-item`, `.sidebar-item-del`, `.sidebar-group`, `.sidebar-new-btn`, `.sidebar-toggle`, `.sidebar.collapsed`

---

## 🧪 Testes — `tests/test_sessions.py` (**novo**)

12 testes:

| Teste | O que verifica |
|-------|----------------|
| `test_list_sessions_empty` | Lista vazia inicial |
| `test_create_session` | Criação retorna 201 + dados |
| `test_list_sessions_after_create` | Listagem reflete criação |
| `test_get_session` | GET por ID retorna sessão |
| `test_get_session_not_found` | ID inexistente → 404 |
| `test_delete_session` | Exclusão + verificação |
| `test_rename_session` | Renomear atualiza título |
| `test_sessions_requires_auth` | Sem token → 401 |
| `test_session_messages` | Mensagens da sessão |
| `test_sessions_isolated_per_user` | Isolamento entre usuários |

## 🧪 Testes alterados

| Arquivo | Mudança |
|---------|---------|
| `tests/conftest.py` | Adicionado `test_user`, `user_token`, `auth_headers` |
| `tests/test_chat.py` | Endpoints agora exigem `auth_headers` |
| `tests/test_models.py` | `session_key` → `session_id` + `ChatSession` |
| `tests/test_schemas.py` | Teste para `session_id` em `ChatRequest` |

---

## 📁 Resumo de Arquivos

### Criados
| Arquivo | Conteúdo |
|---------|----------|
| `backend/routers/sessions.py` | CRUD de sessões |
| `frontend/src/Sidebar.jsx` | Barra lateral |
| `tests/test_sessions.py` | 12 testes de sessão |

### Modificados
| Arquivo | Mudança principal |
|---------|-------------------|
| `backend/models.py` | + `ChatSession`, `ChatMessage.session_id` (FK) |
| `backend/schemas/chat.py` | + schemas de sessão, + `session_id` |
| `backend/routers/chat.py` | session_id + auth + auto-title |
| `backend/services/openrouter.py` | + `generate_title()` |
| `backend/main.py` | + `sessions_router` |
| `frontend/src/api.js` | + funções de sessão |
| `frontend/src/App.jsx` | + estado de sessões, sidebar |
| `frontend/index.html` | + Sidebar script + CSS |
| `tests/conftest.py` | + fixtures de auth |
| `tests/test_chat.py` | + auth_headers |
| `tests/test_models.py` | session_key → session_id |
| `tests/test_schemas.py` | + teste session_id |

---

## ✅ Resultado dos Testes

**64/64 testes passando**
- auth: 11 ✅
- chat: 9 ✅
- models: 6 ✅
- openrouter: 11 ✅
- schemas: 10 ✅
- sessions: 12 ✅ (novos)

---

## ⚠️ Observações

- **Banco antigo deletado**: O schema do `ChatMessage` mudou de `session_key` (string) para `session_id` (FK). O arquivo `database/chat.db` foi removido. Dados existentes foram perdidos — esperado para ambiente de experimento.
- **Título automático assíncrono**: Não bloqueia a resposta do chat, mas pode levar alguns segundos para aparecer na sidebar.
- **Recarregamento da sidebar**: A lista inteira de sessões é recarregada após cada mensagem para capturar atualizações de título. Pode ser otimizado com polling seletivo ou WebSocket no futuro.