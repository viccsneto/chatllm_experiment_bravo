const API_BASE = window.location.origin;

// ── Auth ──────────────────────────────────────────────

function getToken() {
  return localStorage.getItem("access_token");
}

function setToken(token) {
  localStorage.setItem("access_token", token);
}

function clearToken() {
  localStorage.removeItem("access_token");
}

function authHeaders() {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function apiRegister(email, password) {
  const res = await fetch(`${API_BASE}/api/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || "Erro ao cadastrar.");
  setToken(data.access_token);
  return data;
}

async function apiLogin(email, password) {
  const res = await fetch(`${API_BASE}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || "Erro ao fazer login.");
  setToken(data.access_token);
  return data;
}

async function apiLogout() {
  const res = await fetch(`${API_BASE}/api/auth/logout`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
  });
  clearToken();
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || "Erro ao fazer logout.");
  }
  return res.json();
}

async function apiMe() {
  const res = await fetch(`${API_BASE}/api/auth/me`, {
    headers: { ...authHeaders() },
  });
  if (!res.ok) return null;
  return res.json();
}

// ── Sessions ──────────────────────────────────────────

async function apiListSessions() {
  const res = await fetch(`${API_BASE}/api/sessions/`, {
    headers: { ...authHeaders() },
  });
  if (!res.ok) throw new Error("Erro ao listar sessoes.");
  return res.json();
}

async function apiCreateSession() {
  const res = await fetch(`${API_BASE}/api/sessions/`, {
    method: "POST",
    headers: { ...authHeaders() },
  });
  if (!res.ok) throw new Error("Erro ao criar sessao.");
  return res.json();
}

async function apiGetSessionMessages(sessionId) {
  const res = await fetch(`${API_BASE}/api/sessions/${sessionId}/messages`, {
    headers: { ...authHeaders() },
  });
  if (!res.ok) throw new Error("Erro ao buscar mensagens da sessao.");
  return res.json();
}

async function apiDeleteSession(sessionId) {
  const res = await fetch(`${API_BASE}/api/sessions/${sessionId}`, {
    method: "DELETE",
    headers: { ...authHeaders() },
  });
  if (!res.ok) throw new Error("Erro ao deletar sessao.");
}

// ── Chat ──────────────────────────────────────────────

async function sendMessageStream({ message, history, sessionId, signal, onDelta, onTitle }) {
  const response = await fetch(`${API_BASE}/api/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ message, history, session_id: sessionId }),
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
  let lastSessionId = sessionId;

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

      if (payload.session_id && !lastSessionId) {
        lastSessionId = payload.session_id;
      }

      if (payload.title && onTitle) {
        onTitle(payload.title, lastSessionId || payload.session_id);
      }

      if (payload.delta) {
        onDelta(payload.delta);
      }
    }
  }

  return lastSessionId;
}
