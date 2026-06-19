const API_BASE = window.location.origin;

async function sendMessageStream({ message, history, sessionId, onDelta, signal }) {
  const response = await fetch(`${API_BASE}/api/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...getAuthHeaders() },
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
    }
  }
}

// ─── Auth API ────────────────────────────────────────────────────────────────

function getAuthHeaders() {
  const token = localStorage.getItem("access_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function apiRegister(email, password) {
  const response = await fetch(`${API_BASE}/api/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || "Erro ao cadastrar.");
  return data;
}

async function apiLogin(email, password) {
  const response = await fetch(`${API_BASE}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || "Erro ao fazer login.");
  return data;
}

async function apiLogout() {
  const response = await fetch(`${API_BASE}/api/auth/logout`, {
    method: "POST",
    headers: { ...getAuthHeaders() },
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || "Erro ao fazer logout.");
  return data;
}

async function apiGetMe() {
  const response = await fetch(`${API_BASE}/api/auth/me`, {
    headers: { ...getAuthHeaders() },
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || "Erro ao obter usuario.");
  return data;
}

// ─── Session API ─────────────────────────────────────────────────────────────

async function apiListSessions() {
  const response = await fetch(`${API_BASE}/api/sessions`, {
    headers: { ...getAuthHeaders() },
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || "Erro ao listar sessoes.");
  return data.sessions;
}

async function apiCreateSession() {
  const response = await fetch(`${API_BASE}/api/sessions`, {
    method: "POST",
    headers: { ...getAuthHeaders(), "Content-Type": "application/json" },
    body: "{}",
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || "Erro ao criar sessao.");
  return data;
}

async function apiDeleteSession(sessionId) {
  const response = await fetch(`${API_BASE}/api/sessions/${sessionId}`, {
    method: "DELETE",
    headers: { ...getAuthHeaders() },
  });
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(data.detail || "Erro ao deletar sessao.");
  }
}

async function apiGetSessionMessages(sessionId) {
  const response = await fetch(
    `${API_BASE}/api/sessions/${sessionId}/messages`,
    {
      headers: { ...getAuthHeaders() },
    }
  );
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || "Erro ao carregar mensagens.");
  return data;
}
