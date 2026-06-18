const { useEffect, useMemo, useRef, useState } = React;

function createMessageId() {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

function AuthForm({ onAuthSuccess }) {
  const [mode, setMode] = useState("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [authError, setAuthError] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();
    setAuthError("");
    setLoading(true);
    try {
      const fn = mode === "login" ? login : signup;
      const result = await fn(email, password);
      onAuthSuccess(result.user);
    } catch (err) {
      setAuthError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const toggleMode = () => {
    setMode((m) => (m === "login" ? "signup" : "login"));
    setAuthError("");
  };

  return (
    <div style={{
      display: "flex", alignItems: "center", justifyContent: "center",
      height: "100%", width: "100%",
    }}>
      <form onSubmit={handleSubmit} style={{
        display: "flex", flexDirection: "column", gap: "16px",
        width: "100%", maxWidth: "360px", padding: "32px",
      }}>
        <h1 style={{ fontSize: "1.5rem", fontWeight: 600, margin: 0, textAlign: "center" }}>
          ChatLLM Lab
        </h1>
        <p style={{ margin: 0, textAlign: "center", color: "var(--muted)", fontSize: "0.9rem" }}>
          {mode === "login" ? "Entre com sua conta" : "Crie sua conta"}
        </p>

        {authError && (
          <div style={{
            color: "#e53e3e", background: "#fff5f5", padding: "10px 14px",
            borderRadius: "8px", fontSize: "0.85rem", border: "1px solid #fed7d7",
          }}>{authError}</div>
        )}

        <input
          type="email"
          placeholder="Seu email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          style={{
            padding: "10px 14px", borderRadius: "8px", border: "1px solid var(--composer-border)",
            font: "inherit", fontSize: "1rem", outline: "none",
          }}
        />
        <input
          type="password"
          placeholder="Sua senha"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          minLength={mode === "signup" ? 6 : 1}
          style={{
            padding: "10px 14px", borderRadius: "8px", border: "1px solid var(--composer-border)",
            font: "inherit", fontSize: "1rem", outline: "none",
          }}
        />
        <button
          type="submit"
          disabled={loading}
          style={{
            padding: "10px", borderRadius: "8px", border: "none",
            background: "var(--accent)", color: "#fff", fontWeight: 600,
            fontSize: "1rem", cursor: loading ? "not-allowed" : "pointer",
            opacity: loading ? 0.7 : 1,
          }}
        >
          {loading ? "Aguarde..." : mode === "login" ? "Entrar" : "Criar conta"}
        </button>

        <button
          type="button"
          onClick={toggleMode}
          style={{
            background: "none", border: "none", color: "var(--muted)",
            cursor: "pointer", fontSize: "0.85rem", textDecoration: "underline",
          }}
        >
          {mode === "login"
            ? "Nao tem conta? Cadastre-se"
            : "Ja tem conta? Faca login"}
        </button>
      </form>
    </div>
  );
}

function Sidebar({ sessions, activeSessionId, onSelectSession, onNewChat, onDeleteSession, onClose }) {
  return (
    <>
      {/* Overlay para mobile */}
      <div
        onClick={onClose}
        style={{
          position: "fixed", inset: 0, background: "rgba(0,0,0,0.3)",
          zIndex: 98,
        }}
      />
      <aside style={{
        position: "fixed", top: 0, left: 0, bottom: 0,
        width: "260px", background: "#f9f9f9",
        borderRight: "1px solid var(--border)",
        display: "flex", flexDirection: "column",
        zIndex: 99, overflow: "hidden",
      }}>
        <div style={{ padding: "12px", borderBottom: "1px solid var(--border)" }}>
          <button
            onClick={onNewChat}
            style={{
              width: "100%", padding: "10px", borderRadius: "8px",
              border: "1px solid var(--border)", background: "#fff",
              cursor: "pointer", fontSize: "0.9rem", fontWeight: 500,
              color: "var(--text)",
            }}
          >
            + Nova conversa
          </button>
        </div>

        <div style={{ flex: 1, overflowY: "auto", padding: "8px" }}>
          {sessions.length === 0 && (
            <p style={{ textAlign: "center", color: "var(--muted)", fontSize: "0.85rem", marginTop: "24px" }}>
              Nenhuma conversa ainda
            </p>
          )}
          {sessions.map((s) => (
            <div
              key={s.id}
              onClick={() => onSelectSession(s.id)}
              style={{
                display: "flex", alignItems: "center", justifyContent: "space-between",
                padding: "10px 12px", borderRadius: "8px", marginBottom: "4px",
                cursor: "pointer", fontSize: "0.88rem",
                background: s.id === activeSessionId ? "#e8e8e8" : "transparent",
                color: "var(--text)", fontWeight: s.id === activeSessionId ? 600 : 400,
              }}
            >
              <span style={{
                overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", flex: 1,
              }}>
                {s.title}
              </span>
              <button
                onClick={(e) => { e.stopPropagation(); onDeleteSession(s.id); }}
                style={{
                  background: "none", border: "none", cursor: "pointer",
                  color: "var(--muted)", fontSize: "0.8rem", padding: "2px 4px",
                  flexShrink: 0, opacity: 0.5,
                }}
                title="Remover sessao"
              >
                ✕
              </button>
            </div>
          ))}
        </div>
      </aside>
    </>
  );
}

function App() {
  const [user, setUser] = useState(null);
  const [loadingAuth, setLoadingAuth] = useState(true);
  const [sessions, setSessions] = useState([]);
  const [activeSessionId, setActiveSessionId] = useState(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [messages, setMessages] = useState([]);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const messagesRef = useRef(null);
  const abortControllerRef = useRef(null);

  // Verificar sessao ao montar
  useEffect(() => {
    fetchMe()
      .then((u) => {
        setUser(u);
        return refreshSessions();
      })
      .catch(() => {
        setUser(null);
        setMessages([]);
      })
      .finally(() => setLoadingAuth(false));
  }, []);

  useEffect(() => {
    const el = messagesRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages]);

  useEffect(() => {
    return () => {
      abortControllerRef.current?.abort();
    };
  }, []);

  const refreshSessions = async () => {
    try {
      const data = await listSessions();
      setSessions(data.sessions);
      return data.sessions;
    } catch {
      return [];
    }
  };

  const chatHistory = useMemo(
    () => messages.filter((msg) => msg.role === "user" || msg.role === "assistant"),
    [messages]
  );

  const onStop = () => {
    abortControllerRef.current?.abort();
    abortControllerRef.current = null;
    setBusy(false);
  };

  const loadSession = async (sessionId) => {
    try {
      const data = await getSession(sessionId);
      setMessages(
        data.messages.map((m) => ({
          id: createMessageId(),
          role: m.role,
          content: m.content,
        }))
      );
      setActiveSessionId(sessionId);
      setSidebarOpen(false);
    } catch (err) {
      setError(err.message);
    }
  };

  const handleNewChat = async () => {
    try {
      const data = await createSession();
      setActiveSessionId(data.id);
      setMessages([{
        id: createMessageId(),
        role: "assistant",
        content: "Nova conversa. Como posso ajudar voce?",
      }]);
      await refreshSessions();
      setSidebarOpen(false);
    } catch (err) {
      setError(err.message);
    }
  };

  const handleDeleteSession = async (sessionId) => {
    try {
      await deleteSession(sessionId);
      if (activeSessionId === sessionId) {
        setActiveSessionId(null);
        setMessages([]);
      }
      await refreshSessions();
    } catch (err) {
      setError(err.message);
    }
  };

  const onSubmit = async (event) => {
    event.preventDefault();
    const cleaned = text.trim();
    if (!cleaned || busy) return;

    setError("");

    // Se nao ha sessao ativa, cria uma automaticamente
    let sid = activeSessionId;
    if (!sid) {
      try {
        const data = await createSession();
        sid = data.id;
        setActiveSessionId(sid);
        refreshSessions();
      } catch (err) {
        setError(err.message);
        return;
      }
    }

    const userMessage = { id: createMessageId(), role: "user", content: cleaned };
    const assistantMessageId = createMessageId();

    setMessages((prev) => [
      ...prev,
      userMessage,
      { id: assistantMessageId, role: "assistant", content: "" },
    ]);
    setText("");
    setBusy(true);
    const abortController = new AbortController();
    abortControllerRef.current = abortController;

    try {
      await sendMessageStream({
        message: cleaned,
        history: chatHistory,
        sessionId: sid,
        signal: abortController.signal,
        onDelta: (delta) => {
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === assistantMessageId
                ? { ...msg, content: `${msg.content}${delta}` }
                : msg
            )
          );
        },
      });

      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === assistantMessageId && !msg.content.trim()
            ? { ...msg, content: "Nao foi possivel obter resposta do modelo agora." }
            : msg
        )
      );

      // Atualizar lista de sessoes (para pegar o titulo gerado)
      await refreshSessions();
    } catch (err) {
      const aborted = err?.name === "AbortError";
      if (!aborted) {
        setError(err.message || "Falha inesperada ao gerar resposta.");
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === assistantMessageId
              ? { ...msg, content: msg.content.trim() ? msg.content : "Nao foi possivel obter resposta do modelo agora." }
              : msg
          )
        );
      } else {
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === assistantMessageId && !msg.content.trim()
              ? { ...msg, content: "Resposta interrompida." }
              : msg
          )
        );
      }
    } finally {
      // Atualiza sidebar mesmo em caso de erro (titulo pode ter sido gerado)
      refreshSessions();
      abortControllerRef.current = null;
      setBusy(false);
    }
  };

  const handleLogout = async () => {
    try {
      await logout();
    } catch { /* ignore */ }
    setUser(null);
    setSessions([]);
    setActiveSessionId(null);
    setMessages([]);
  };

  // Tela de carregamento
  if (loadingAuth) {
    return (
      <main className="app-shell">
        <div style={{
          display: "flex", alignItems: "center", justifyContent: "center",
          height: "100%", fontSize: "1rem", color: "var(--muted)",
        }}>
          Carregando...
        </div>
      </main>
    );
  }

  // Tela de login
  if (!user) {
    return (
      <main className="app-shell">
        <AuthForm onAuthSuccess={async (u) => {
          setUser(u);
          await refreshSessions();
        }} />
      </main>
    );
  }

  // Chat autenticado com sidebar
  return (
    <div style={{ display: "flex", height: "100%", width: "100%" }}>
      {/* Sidebar */}
      {sidebarOpen && (
        <Sidebar
          sessions={sessions}
          activeSessionId={activeSessionId}
          onSelectSession={loadSession}
          onNewChat={handleNewChat}
          onDeleteSession={handleDeleteSession}
          onClose={() => setSidebarOpen(false)}
        />
      )}

      {/* Main content */}
      <main className="app-shell" style={{ flex: 1, minWidth: 0 }}>
        <header className="app-header" style={{
          display: "flex", justifyContent: "space-between", alignItems: "center",
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <button
              onClick={() => setSidebarOpen(!sidebarOpen)}
              style={{
                background: "none", border: "none", cursor: "pointer",
                padding: "4px", color: "var(--text)", fontSize: "1.2rem",
              }}
              aria-label="Abrir sidebar"
            >
              ☰
            </button>
            <div className="brand">ChatLLM Lab</div>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
            <span style={{ fontSize: "0.85rem", color: "var(--muted)" }}>{user.email}</span>
            <button
              onClick={handleLogout}
              style={{
                background: "none", border: "1px solid var(--border)", borderRadius: "6px",
                padding: "4px 12px", cursor: "pointer", fontSize: "0.85rem",
                color: "var(--text)",
              }}
            >
              Sair
            </button>
          </div>
        </header>

        <section className="messages" aria-live="polite" ref={messagesRef}>
          <div className="messages-inner">
            {messages.length === 0 && (
              <div style={{
                textAlign: "center", color: "var(--muted)", marginTop: "60px",
                fontSize: "0.95rem",
              }}>
                Selecione uma conversa ou inicie uma nova.
              </div>
            )}
            {messages.map((msg) => (
              <article key={msg.id} className={`bubble ${msg.role}`}>
                <MessageContent content={msg.content} />
              </article>
            ))}
          </div>
        </section>

        <Composer
          text={text}
          busy={busy}
          error={error}
          onChangeText={setText}
          onSubmit={onSubmit}
          onStop={onStop}
        />

        <div className="warning-banner">Lembre-se, voce precisa focar no experimento!!!</div>
      </main>
    </div>
  );
}

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(<App />);

