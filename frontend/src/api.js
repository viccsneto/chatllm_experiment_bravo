const API_BASE = window.location.origin;

function getAuthHeaders() {
  const token = localStorage.getItem("access_token");
  const headers = { "Content-Type": "application/json" };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  return headers;
}

async function sendMessageStream({ message, history, sessionId, onDelta, signal }) {
  const response = await fetch(`${API_BASE}/api/chat/stream`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify({ message, history, session_id: sessionId }),
    signal,
  });

  if (!response.ok) {
    if (response.status === 401) {
      localStorage.removeItem("access_token");
      localStorage.removeItem("user_email");
      window.location.reload();
      throw new Error("Sessao expirada. Faca login novamente.");
    }
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

async function apiFetch(url, options = {}) {
  const res = await fetch(`${API_BASE}${url}`, {
    ...options,
    headers: { ...getAuthHeaders(), ...options.headers },
  });
  if (res.status === 401) {
    localStorage.removeItem("access_token");
    localStorage.removeItem("user_email");
    window.location.reload();
    throw new Error("Sessao expirada.");
  }
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || "Erro na requisicao.");
  }
  return res.json();
}

async function listSessions() {
  const data = await apiFetch("/api/sessions");
  return data.sessions;
}

async function createSession() {
  const data = await apiFetch("/api/sessions", {
    method: "POST",
    body: JSON.stringify({ title: "Nova Conversa" }),
  });
  return data;
}

async function deleteSession(sessionId) {
  await apiFetch(`/api/sessions/${sessionId}`, { method: "DELETE" });
}

async function fetchSessionMessages(sessionId) {
  const data = await apiFetch(`/api/sessions/${sessionId}/messages`);
  return data.messages;
}
