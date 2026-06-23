const API_BASE = window.location.origin;

// --- Auth API ---

async function apiRequest(method, path, body = null, token = null) {
  const headers = { "Content-Type": "application/json" };
  if (token) headers["token"] = token;

  const opts = { method, headers };
  if (body) opts.body = JSON.stringify(body);

  const response = await fetch(`${API_BASE}${path}`, opts);
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.detail || `Erro ${response.status}`);
  }
  return data;
}

function getToken() {
  return localStorage.getItem("auth_token");
}

function setToken(token) {
  localStorage.setItem("auth_token", token);
}

function clearToken() {
  localStorage.removeItem("auth_token");
}

async function login(email, password) {
  const data = await apiRequest("POST", "/api/auth/login", { email, password });
  setToken(data.token);
  return data;
}

async function signup(email, password) {
  const data = await apiRequest("POST", "/api/auth/signup", { email, password });
  setToken(data.token);
  return data;
}

async function logout() {
  const token = getToken();
  if (token) {
    try {
      await apiRequest("POST", "/api/auth/logout", null, token);
    } catch { /* ignore */ }
  }
  clearToken();
}

async function checkAuth() {
  const token = getToken();
  if (!token) return null;
  try {
    return await apiRequest("GET", "/api/auth/me", null, token);
  } catch {
    clearToken();
    return null;
  }
}

// --- Chat API ---

async function listSessions() {
  const token = getToken();
  return await apiRequest("GET", "/api/sessions", null, token);
}

async function createSession() {
  const token = getToken();
  return await apiRequest("POST", "/api/sessions", {}, token);
}

async function getSessionMessages(sessionId) {
  const token = getToken();
  return await apiRequest("GET", `/api/sessions/${sessionId}/messages`, null, token);
}

async function deleteSession(sessionId) {
  const token = getToken();
  return await apiRequest("DELETE", `/api/sessions/${sessionId}`, null, token);
}

async function sendMessageStream({ message, history, sessionId, onDelta, signal }) {
  const body = { message, history };
  if (sessionId !== null && sessionId !== undefined) body.session_id = sessionId;

  const response = await fetch(`${API_BASE}/api/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    signal,
  });

  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(data.detail || `Erro ${response.status}`);
  }

  if (!response.body) {
    throw new Error("Streaming nao suportado no ambiente atual.");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";
  let resolvedSessionId = sessionId;

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

      if (payload.session_id && resolvedSessionId === undefined) {
        resolvedSessionId = payload.session_id;
      }

      if (payload.delta) {
        onDelta(payload.delta, resolvedSessionId);
      }
    }
  }

  return resolvedSessionId;
}
