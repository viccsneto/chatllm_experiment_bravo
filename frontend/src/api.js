const API_BASE = window.location.origin;

async function getErrorMessage(response, fallback) {
  const body = await response.json().catch(() => ({}));
  if (typeof body?.detail === "string") return body.detail;
  if (Array.isArray(body?.detail) && body.detail[0]?.msg) return body.detail[0].msg;
  return fallback;
}

async function getCurrentUser() {
  const response = await fetch(`${API_BASE}/api/auth/me`, {
    credentials: "same-origin",
  });

  if (response.status === 401) return null;
  if (!response.ok) {
    throw new Error(await getErrorMessage(response, "Erro ao verificar a autenticacao."));
  }
  return response.json();
}

async function submitCredentials(path, credentials) {
  const response = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "same-origin",
    body: JSON.stringify(credentials),
  });

  if (!response.ok) {
    throw new Error(await getErrorMessage(response, "Nao foi possivel autenticar."));
  }
  return response.json();
}

function registerUser(credentials) {
  return submitCredentials("/api/auth/register", credentials);
}

function loginUser(credentials) {
  return submitCredentials("/api/auth/login", credentials);
}

async function logoutUser() {
  const response = await fetch(`${API_BASE}/api/auth/logout`, {
    method: "POST",
    credentials: "same-origin",
  });

  if (!response.ok) {
    throw new Error(await getErrorMessage(response, "Nao foi possivel sair."));
  }
}

async function listChatSessions() {
  const response = await fetch(`${API_BASE}/api/sessions`, {
    credentials: "same-origin",
  });
  if (!response.ok) {
    throw new Error(await getErrorMessage(response, "Erro ao carregar conversas."));
  }
  return response.json();
}

async function createChatSession() {
  const response = await fetch(`${API_BASE}/api/sessions`, {
    method: "POST",
    credentials: "same-origin",
  });
  if (!response.ok) {
    throw new Error(await getErrorMessage(response, "Erro ao criar conversa."));
  }
  return response.json();
}

async function getChatSession(sessionId) {
  const response = await fetch(`${API_BASE}/api/sessions/${sessionId}`, {
    credentials: "same-origin",
  });
  if (!response.ok) {
    throw new Error(await getErrorMessage(response, "Erro ao carregar a conversa."));
  }
  return response.json();
}

async function sendMessageStream({ message, sessionId, onDelta, onDone, signal }) {
  const response = await fetch(`${API_BASE}/api/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "same-origin",
    body: JSON.stringify({ message, session_id: sessionId }),
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

      if (payload.done) {
        onDone?.(payload);
      }
    }
  }
}
