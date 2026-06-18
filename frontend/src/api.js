const API_BASE = window.location.origin;

function getToken() {
  return localStorage.getItem("auth_token");
}

function setToken(token) {
  if (token) {
    localStorage.setItem("auth_token", token);
  } else {
    localStorage.removeItem("auth_token");
  }
}

// ── Auth ──────────────────────────────────────────────────────────

async function apiFetch(path, options) {
  options = options || {};
  var headers = { "Content-Type": "application/json" };
  var token = getToken();
  if (token) {
    headers["Authorization"] = "Bearer " + token;
  }
  var res = await fetch(API_BASE + path, {
    method: options.method || "GET",
    headers: headers,
    body: options.body ? JSON.stringify(options.body) : undefined,
  });
  var data = await res.json().catch(function() { return null; });
  if (!res.ok) {
    // Se 401, limpa token e redireciona
    if (res.status === 401) {
      setToken(null);
    }
    var msg = (data && (data.detail || data.message)) || "Erro " + res.status;
    throw new Error(msg);
  }
  return data;
}

async function signup(email, password) {
  const result = await apiFetch("/api/auth/signup", {
    method: "POST",
    body: { email, password },
  });
  if (result.token) setToken(result.token);
  return result;
}

async function login(email, password) {
  const result = await apiFetch("/api/auth/login", {
    method: "POST",
    body: { email, password },
  });
  if (result.token) setToken(result.token);
  return result;
}

async function logout() {
  setToken(null);
  return { message: "Logout realizado com sucesso." };
}

async function fetchMe() {
  return apiFetch("/api/auth/me");
}

// ── Sessions ──────────────────────────────────────────────────────

async function createSession() {
  return apiFetch("/api/sessions", { method: "POST", body: {} });
}

async function listSessions() {
  return apiFetch("/api/sessions");
}

async function getSession(sessionId) {
  return apiFetch("/api/sessions/" + sessionId);
}

async function deleteSession(sessionId) {
  return apiFetch("/api/sessions/" + sessionId, { method: "DELETE" });
}

// ── Chat ──────────────────────────────────────────────────────────

async function sendMessageStream({ message, history, sessionId, onDelta, signal }) {
  var headers = { "Content-Type": "application/json" };
  var token = getToken();
  if (token) {
    headers["Authorization"] = "Bearer " + token;
  }
  var response = await fetch(API_BASE + "/api/chat/stream", {
    method: "POST",
    headers: headers,
    body: JSON.stringify({ message: message, history: history, session_id: sessionId }),
    signal: signal,
  });

  if (!response.ok) {
    var body = await response.json().catch(function() { return {}; });
    var detail = (body && body.detail) || "Erro ao enviar mensagem para o servidor.";
    throw new Error(detail);
  }

  if (!response.body) {
    throw new Error("Streaming nao suportado no ambiente atual.");
  }

  var reader = response.body.getReader();
  var decoder = new TextDecoder("utf-8");
  var buffer = "";

  while (true) {
    var result = await reader.read();
    if (result.done) break;

    buffer += decoder.decode(result.value, { stream: true });
    var events = buffer.split("\n\n");
    buffer = events.pop() || "";

    for (var i = 0; i < events.length; i++) {
      var rawEvent = events[i];
      var lines = rawEvent.split("\n");
      var dataLine = null;
      for (var j = 0; j < lines.length; j++) {
        if (lines[j].indexOf("data:") === 0) {
          dataLine = lines[j];
          break;
        }
      }
      if (!dataLine) continue;

      var payloadText = dataLine.slice(5).trim();
      if (!payloadText) continue;

      var payload;
      try {
        payload = JSON.parse(payloadText);
      } catch (e) {
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
