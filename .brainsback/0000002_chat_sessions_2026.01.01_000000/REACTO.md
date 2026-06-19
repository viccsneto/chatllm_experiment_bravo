# Proof of Mastery (REACTO)

> Explain it to prove you own it.

**Hard rule**: AI agents must not edit this file and must not draft paste-ready content for it.

## R — Repeat (The Problem)
é preciso que exista a possibilidade do usuário manter diferentes sessões de chat, que poderão ser acessadas através de uma barra lateral. Para organização, cada sessão deve ter um título que serão gerados automaticamente com base no conteúdo daquela conversa. Adicionalmente, as sessões que tiveram interação mais recente devem ser listadas primeiro. Por fim, é imporante que, durante as sessões, o agente foque em gerar as respostas com base no contexto daquela sessão específica, apesar de poder também construir um conexto geral do perfil do usuário com base no conteúdo adquirido através de outras sessões.

## E — Examples
_Provide concrete inputs and expected outputs that demonstrate the correctness. Base them on observable behavior._

- **Happy Path Input**: Usuário clica em nova sessão.
  **Output**: Após o usuário ter clicado em nova sesão, um novo chat é aberto. Após a primeira mensagem do usuário ter sido enviada, é gerado através de IA um título que represente o contexto da mensagem enviada pelo usuário, e, como consequência, represente o contexto daquele chat.
  
  - **Happy Path Input**: Usuário clica em uma sessão da lista de sessões na barra lateral;
  **Output**: Após o usuário ter clicado em uma sessão específica, aquele chat é aberto e seu histórico é carregado. Assim, o usuário consegue continuar conversando com o agente com base no contexto daquele chat.

- **Edge Case Input**: O usuário não está logado.
  **Output**: O usuário que não está logado não deve conseguir armazenar o histórico de sessões distintas.

## A — Approach
Para atingir o que foi proposto  na sessão de 'R — Repeat (The Problem)' , foi necessário  armaznar informações correspondente a diferentes sessões no banco de dados, ajsutando o modelo existente para que pudesse armazenar tais dados. Além disso, foi necessário criar rotas da API para o gerenciamento dessas sessões e alterar rotas já existentes para gerenciarem também informações referentes as sessões, como o session_id. No frontend, foi necessário implementar a barra lateral, que lista as sessões, e a geração automatica do titulo com base no contexto daquela sessão. 

## C — Code
Entre as modificações de código mais criticas, estão: 

1. Modificações necessárias para que as informações referntes as sessões fossem armazenadas no banco de dados:
- `backend/models.py`: Novo modelo `ChatSession` (user_id, title, created_at, updated_at) com FK para User; `ChatMessage` migrado de `session_key` para `session_id` (FK para ChatSession); relacionamentos ORM configurados.
- `backend/schemas/session.py` (novo): Schemas `SessionCreate`, `SessionResponse`, `SessionListResponse`.
- `backend/schemas/chat.py`: Adicionado campo `session_id` opcional em `ChatRequest` e `ChatResponse`.

2. Modificações necessárias para a realização de requisições considerando o novo cenário de armazenamento e gerenciamento de diversas sessões:
- `backend/routers/sessions.py` (novo): Rotas CRUD para sessões (`GET /api/sessions`, `POST /api/sessions`, `GET /api/sessions/{id}`, `DELETE /api/sessions/{id}`), todas protegidas por autenticação.
- `backend/routers/chat.py`: Rotas de chat agora exigem autenticação; aceitam `session_id`; criam sessão automaticamente se não especificada; atualizam `updated_at`; expõem `GET /api/sessions/{id}/messages` para carregar histórico.
- `backend/main.py`: Registrado router de sessões.
- `frontend/src/api.js`: Adicionadas funções `apiListSessions`, `apiCreateSession`, `apiDeleteSession`, `apiGetSessionMessages`; `sendMessageStream` agora envia `session_id` e token de autenticação.

3. Modificação necessária para a geração automática de título para cada sessão do usuário:
- `backend/services/title.py` (novo): Serviço que gera título automático via OpenRouter com base na primeira mensagem do usuário.

4. Modificações necessárias visando a visualização e usabilidade das novas funcionalidades na aplicação:
- `frontend/src/App.jsx`: Barra lateral com lista de sessões ordenadas por `updated_at` (mais recentes primeiro); botão "Nova sessão"; seleção de sessão carrega histórico; deleção de sessão; criação automática de sessão ao enviar mensagem sem sessão ativa.


## T — Tests
Para validar o que foi implementado, foi relizado 50 testes automatizado rodando com SQLite em memória. Os testes incluem a validação de criação, consulta por session_id, role e persistência de texo longo. Além disso, testes de API de sessões cobrem CRUD completo, autenticação e isolamento entre usuáiros. Por fim, testes de chat verificam que autenticação é exigida e que endpoints respondem corretamente.

Os arquivos dos testes automatizados estão todos dentro da pasta `tests`. Relativo ao gerenciamento de sessões, especificamente, é possível ver um exemplo de teste em:  `tests/test_sessions.py`, exposto abaixo:
´´´
from __future__ import annotations

from fastapi.testclient import TestClient


class TestSessionsAPI:
    def test_list_sessions_requires_auth(self, client: TestClient):
        response = client.get("/api/sessions")
        assert response.status_code == 401

    def test_create_session_requires_auth(self, client: TestClient):
        response = client.post("/api/sessions", json={})
        assert response.status_code == 401

    def test_create_and_list_sessions(self, client: TestClient, auth_headers):
        # Create first session
        resp1 = client.post("/api/sessions", json={}, headers=auth_headers)
        assert resp1.status_code == 201
        data1 = resp1.json()
        assert data1["title"] == "Nova conversa"
        assert data1["id"] is not None

        # Create second session
        resp2 = client.post("/api/sessions", json={}, headers=auth_headers)
        assert resp2.status_code == 201
        data2 = resp2.json()

        # List sessions (most recent first)
        resp_list = client.get("/api/sessions", headers=auth_headers)
        assert resp_list.status_code == 200
        data = resp_list.json()
        assert len(data["sessions"]) == 2
        # Most recent should be first
        assert data["sessions"][0]["id"] == data2["id"]

    def test_get_session(self, client: TestClient, auth_headers):
        create_resp = client.post("/api/sessions", json={}, headers=auth_headers)
        session_id = create_resp.json()["id"]

        resp = client.get(f"/api/sessions/{session_id}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["id"] == session_id

    def test_get_session_not_found(self, client: TestClient, auth_headers):
        resp = client.get("/api/sessions/99999", headers=auth_headers)
        assert resp.status_code == 404

    def test_delete_session(self, client: TestClient, auth_headers):
        create_resp = client.post("/api/sessions", json={}, headers=auth_headers)
        session_id = create_resp.json()["id"]

        resp = client.delete(f"/api/sessions/{session_id}", headers=auth_headers)
        assert resp.status_code == 204

        # Verify it's gone
        resp_get = client.get(f"/api/sessions/{session_id}", headers=auth_headers)
        assert resp_get.status_code == 404

    def test_delete_session_not_found(self, client: TestClient, auth_headers):
        resp = client.delete("/api/sessions/99999", headers=auth_headers)
        assert resp.status_code == 404

    def test_sessions_isolated_per_user(self, client: TestClient, auth_headers):
        """Sessoes de um usuario nao devem ser visiveis para outro."""
        # Create session for user 1
        client.post("/api/sessions", json={}, headers=auth_headers)

        # Register and login as user 2
        client.post("/api/auth/register", json={"email": "user2@teste.com", "password": "123456"})
        resp_login = client.post("/api/auth/login", json={"email": "user2@teste.com", "password": "123456"})
        token2 = resp_login.json()["access_token"]
        headers2 = {"Authorization": f"Bearer {token2}"}

        resp_list = client.get("/api/sessions", headers=headers2)
        assert resp_list.status_code == 200
        assert len(resp_list.json()["sessions"]) == 0
      ´´´

Adicionalmente, foi necessário realizar testes manuais, interagindo com a aplicação. Neles, foi verificado que a geração automatizada de títulos não estava funcionando corretamente, o que foi resolvido através da reescrita do endpoint de streaming para capturar session.id e a flag is_new_session antes do generator, além de usar db.query().update() (SQL direto) em vez de modificar o objeto ORM após commit. Assim, a geração de título passou a usar o session_id capturado para fazer update via query, evitando o problema de expiração. Após as alterações realizadas, foi comprovado via teste manual que a geração automatizada de título está funcionando corretamente.


## O — Optimize
_Address Big(O) complexity, note that sometimes it doesn't apply, trade-offs, constraints, and opportunities for future improvement._
A geração de título via OpenRouter adiciona latência extra na primeira resposta, o fallback local (primeiras palavras) é mais rápido e não depende de API externa. Entretanto, é  possível que a geração de título via IA seja mais preciso e inteligente. 

Além disso, outra possibilidade interessante, seria a geração de título de forma assíncrona, que seria fora do fluxo principal da resposta da primeira mensagem, visando não gerar atraso adicional para o usuário.

Outra melhoria interessante seria a paginação na listagem de sessões, pois se um usuário tiver centenas de sessões, carregar todas de uma vez é ineficiente. Implementar paginação (limit/offset) ou infinite scroll poderia ser melhor.