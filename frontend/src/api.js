const API_BASE = window.location.origin;

/** Configuracao padrao de fetch com cookies e protecao CSRF. */
function apiFetch(url, options = {}) {
  const headers = {
    "Content-Type": "application/json",
    "X-Requested-With": "XMLHttpRequest",
    ...options.headers,
  };
  return fetch(url, {
    ...options,
    headers,
    credentials: "include",
  });
}

/* ── Auth ────────────────────────────────────────── */

async function apiSignup(email, password) {
  const res = await apiFetch(`${API_BASE}/api/auth/signup`, {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || "Erro no cadastro.");
  return data;
}

async function apiLogin(email, password) {
  const res = await apiFetch(`${API_BASE}/api/auth/login`, {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || "Erro no login.");
  return data;
}

async function apiLogout() {
  const res = await apiFetch(`${API_BASE}/api/auth/logout`, {
    method: "POST",
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || "Erro no logout.");
  return data;
}

async function apiMe() {
  const res = await apiFetch(`${API_BASE}/api/auth/me`);
  if (!res.ok) return null;
  return res.json();
}

/* ── Sessions ────────────────────────────────────── */

async function apiListSessions() {
  const res = await apiFetch(`${API_BASE}/api/sessions`);
  if (!res.ok) throw new Error("Erro ao carregar sessoes.");
  return res.json();
}

async function apiCreateSession() {
  const res = await apiFetch(`${API_BASE}/api/sessions`, {
    method: "POST",
    body: JSON.stringify({}),
  });
  if (!res.ok) throw new Error("Erro ao criar sessao.");
  return res.json();
}

async function apiGetSessionMessages(sessionId) {
  const res = await apiFetch(`${API_BASE}/api/sessions/${sessionId}/messages`);
  if (!res.ok) throw new Error("Erro ao carregar mensagens.");
  return res.json();
}

async function apiUpdateSessionTitle(sessionId, title) {
  const res = await apiFetch(`${API_BASE}/api/sessions/${sessionId}/title`, {
    method: "PUT",
    body: JSON.stringify({ title }),
  });
  if (!res.ok) throw new Error("Erro ao atualizar titulo.");
  return res.json();
}

/* ── Chat ────────────────────────────────────────── */

async function sendMessageStream({ message, sessionId, history, onDelta, onDone, signal }) {
  const response = await apiFetch(`${API_BASE}/api/chat/stream`, {
    method: "POST",
    body: JSON.stringify({ message, session_id: sessionId, history }),
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
