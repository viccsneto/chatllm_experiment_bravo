const API_BASE = window.location.origin;

/* ── Auth ────────────────────────────────────────────────── */

function getToken() {
  return localStorage.getItem("auth_token");
}

function setToken(token) {
  localStorage.setItem("auth_token", token);
}

function clearToken() {
  localStorage.removeItem("auth_token");
}

function isAuthenticated() {
  return !!getToken();
}

async function authFetch(url, options = {}) {
  const token = getToken();
  const headers = { "Content-Type": "application/json", ...options.headers };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  const response = await fetch(`${API_BASE}${url}`, { ...options, headers });
  return response;
}

async function register(email, password) {
  const response = await authFetch("/api/auth/register", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || "Erro ao cadastrar");
  setToken(data.access_token);
  return data;
}

async function login(email, password) {
  const response = await authFetch("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || "Erro ao fazer login");
  setToken(data.access_token);
  return data;
}

async function logout() {
  const response = await authFetch("/api/auth/logout", { method: "POST" });
  clearToken();
  return response.ok;
}

async function fetchMe() {
  const response = await authFetch("/api/auth/me");
  if (!response.ok) {
    clearToken();
    return null;
  }
  const data = await response.json();
  return data;
}

/* ── Sessions ─────────────────────────────────────────────── */

async function fetchSessions() {
  const response = await authFetch("/api/sessions");
  if (!response.ok) throw new Error("Erro ao carregar sessoes");
  return response.json();
}

async function createSession() {
  const response = await authFetch("/api/sessions", {
    method: "POST",
    body: JSON.stringify({}),
  });
  if (!response.ok) throw new Error("Erro ao criar sessao");
  return response.json();
}

async function renameSession(sessionId, title) {
  const response = await authFetch(`/api/sessions/${sessionId}`, {
    method: "PATCH",
    body: JSON.stringify({ title }),
  });
  if (!response.ok) throw new Error("Erro ao renomear sessao");
  return response.json();
}

async function deleteSession(sessionId) {
  const response = await authFetch(`/api/sessions/${sessionId}`, {
    method: "DELETE",
  });
  if (!response.ok) throw new Error("Erro ao deletar sessao");
}

/* ── Chat ────────────────────────────────────────────────── */

async function sendMessageStream({ message, session_id, history, onDelta, signal }) {
  const payload = { message, history };
  if (session_id != null) payload.session_id = session_id;

  const response = await authFetch("/api/chat/stream", {
    method: "POST",
    body: JSON.stringify(payload),
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
