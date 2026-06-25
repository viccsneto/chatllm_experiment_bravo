const API_BASE = window.location.origin;

function getToken() {
  return localStorage.getItem("token");
}

function setToken(token) {
  localStorage.setItem("token", token);
}

function clearToken() {
  localStorage.removeItem("token");
}

async function apiSignup(email, password) {
  const res = await fetch(`${API_BASE}/api/auth/signup`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || "Erro ao cadastrar");
  setToken(data.token);
  return data;
}

async function apiLogin(email, password) {
  const res = await fetch(`${API_BASE}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || "Erro ao entrar");
  setToken(data.token);
  return data;
}

async function apiLogout() {
  const token = getToken();
  if (!token) return;
  await fetch(`${API_BASE}/api/auth/logout`, {
    method: "POST",
    headers: { "Content-Type": "application/json", token },
  });
  clearToken();
}

async function apiMe() {
  const token = getToken();
  if (!token) return null;
  const res = await fetch(`${API_BASE}/api/auth/me`, {
    headers: { token },
  });
  if (!res.ok) {
    clearToken();
    return null;
  }
  return res.json();
}

function _authHeaders() {
  const headers = { "Content-Type": "application/json" };
  const token = getToken();
  if (token) headers["token"] = token;
  return headers;
}

async function apiCreateSession() {
  const res = await fetch(`${API_BASE}/api/sessions`, {
    method: "POST",
    headers: _authHeaders(),
  });
  if (!res.ok) throw new Error("Erro ao criar sessao");
  return res.json();
}

async function apiListSessions() {
  const res = await fetch(`${API_BASE}/api/sessions`, {
    headers: _authHeaders(),
  });
  if (!res.ok) throw new Error("Erro ao listar sessoes");
  return res.json();
}

async function apiGetSessionMessages(sessionId) {
  const res = await fetch(`${API_BASE}/api/sessions/${sessionId}/messages`, {
    headers: _authHeaders(),
  });
  if (!res.ok) throw new Error("Erro ao carregar mensagens");
  return res.json();
}

async function apiDeleteSession(sessionId) {
  const res = await fetch(`${API_BASE}/api/sessions/${sessionId}`, {
    method: "DELETE",
    headers: _authHeaders(),
  });
  if (!res.ok) throw new Error("Erro ao deletar sessao");
}

async function sendMessageStream({ message, sessionId, history, onDelta, onDone, signal }) {
  const headers = _authHeaders();

  const body = { message, history };
  if (sessionId) body.session_id = sessionId;

  const response = await fetch(`${API_BASE}/api/chat/stream`, {
    method: "POST",
    headers,
    body: JSON.stringify(body),
    signal,
  });

  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    const detail = body?.detail || "Erro ao enviar mensagem para o servidor.";
    throw new Error(detail);
  }

  if (!response.body) {
    throw new Error("Streaming nao suportado no ambiente atual.");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const events = buffer.split("\n\n");
    buffer = events.pop() || "";

    for (const rawEvent of events) {
      const line = rawEvent
        .split("\n")
        .find((part) => part.startsWith("data:"));
      if (!line) continue;

      const payloadText = line.slice(5).trim();
      if (!payloadText) continue;

      let payload;
      try {
        payload = JSON.parse(payloadText);
      } catch {
        continue;
      }

      if (payload.error) {
        throw new Error(payload.error);
      }

      if (payload.delta) {
        onDelta(payload.delta);
      }

      if (payload.done && onDone) {
        onDone(payload);
      }
    }
  }
}
