const { useEffect, useMemo, useRef, useState, useCallback } = React;

function createMessageId() {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

// ── Auth Screen ───────────────────────────────────────────────────────────────

function AuthScreen({ onAuthSuccess }) {
  const [mode, setMode] = useState("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const emailRef = useRef(null);

  useEffect(() => {
    emailRef.current?.focus();
  }, [mode]);

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError("");
    const trimmedEmail = email.trim();
    if (!trimmedEmail || !password) {
      setError("Preencha todos os campos.");
      return;
    }
    setLoading(true);
    try {
      const result =
        mode === "register"
          ? await registerUser(trimmedEmail, password)
          : await loginUser(trimmedEmail, password);
      localStorage.setItem("auth_token", result.access_token);
      localStorage.setItem("auth_email", result.email);
      onAuthSuccess(result.email);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-screen">
      <div className="auth-card">
        <h1 className="auth-title">ChatLLM Lab</h1>
        <p className="auth-subtitle">
          {mode === "login" ? "Entre com sua conta" : "Crie sua conta"}
        </p>
        {error && <div className="note error">{error}</div>}
        <form onSubmit={handleSubmit} className="auth-form">
          <input ref={emailRef} type="email" placeholder="Seu email" value={email} onChange={(e) => setEmail(e.target.value)} disabled={loading} autoComplete="email" className="auth-input" />
          <input type="password" placeholder="Sua senha" value={password} onChange={(e) => setPassword(e.target.value)} disabled={loading} autoComplete={mode === "register" ? "new-password" : "current-password"} className="auth-input" />
          <button type="submit" disabled={loading} className="auth-btn">
            {loading ? "Aguarde..." : mode === "login" ? "Entrar" : "Cadastrar"}
          </button>
        </form>
        <p className="auth-toggle">
          {mode === "login" ? (
            <>Nao tem conta? <button className="link-btn" onClick={() => { setMode("register"); setError(""); }}>Cadastre-se</button></>
          ) : (
            <>Ja tem conta? <button className="link-btn" onClick={() => { setMode("login"); setError(""); }}>Entrar</button></>
          )}
        </p>
      </div>
    </div>
  );
}

// ── Sidebar ───────────────────────────────────────────────────────────────────

function Sidebar({ sessions, currentSessionId, onSelectSession, onNewSession, onDeleteSession, onToggle, open }) {
  return (
    <>
      {open && <div className="sidebar-overlay" onClick={onToggle} />}
      <aside className={`sidebar ${open ? "sidebar--open" : ""}`}>
        <div className="sidebar-header">
          <button className="new-chat-btn" onClick={onNewSession}>
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <line x1="8" y1="2" x2="8" y2="14" /><line x1="2" y1="8" x2="14" y2="8" />
            </svg>
            Novo Chat
          </button>
        </div>
        <div className="sidebar-list">
          {sessions.length === 0 && <p className="sidebar-empty">Nenhuma sessao ainda</p>}
          {sessions.map((s) => (
            <div key={s.id} className={`sidebar-item ${s.id === currentSessionId ? "sidebar-item--active" : ""}`} onClick={() => onSelectSession(s.id)}>
              <span className="sidebar-item-title">{s.title || "Nova conversa"}</span>
              <button className="sidebar-item-del" title="Deletar" onClick={(e) => { e.stopPropagation(); onDeleteSession(s.id); }}>
                <svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
                  <line x1="2" y1="2" x2="10" y2="10" /><line x1="10" y1="2" x2="2" y2="10" />
                </svg>
              </button>
            </div>
          ))}
        </div>
      </aside>
    </>
  );
}

// ── Main App ──────────────────────────────────────────────────────────────────

function App() {
  const [user, setUser] = useState(null);
  const [checkingAuth, setCheckingAuth] = useState(true);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [sessions, setSessions] = useState([]);
  const [currentSessionId, setCurrentSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [loadingMessages, setLoadingMessages] = useState(false);
  const messagesRef = useRef(null);
  const abortControllerRef = useRef(null);

  const chatHistory = useMemo(
    () => messages.filter((msg) => msg.role === "user" || msg.role === "assistant"),
    [messages]
  );

  // Load sessions
  const loadSessions = useCallback(async () => {
    try {
      const list = await listSessions();
      setSessions(list);
    } catch (err) {
      console.error("Erro ao carregar sessoes:", err);
    }
  }, []);

  // Load messages for a session
  const loadMessages = useCallback(async (sessionId) => {
    setLoadingMessages(true);
    try {
      const msgs = await getSessionMessages(sessionId);
      setMessages(
        msgs.map((m) => ({
          id: createMessageId(),
          role: m.role,
          content: m.content,
        }))
      );
    } catch (err) {
      console.error("Erro ao carregar mensagens:", err);
      setMessages([]);
    } finally {
      setLoadingMessages(false);
    }
  }, []);

  // Initial auth check
  useEffect(() => {
    const token = localStorage.getItem("auth_token");
    const email = localStorage.getItem("auth_email");
    if (token && email) {
      getMe()
        .then((data) => {
          setUser(data.email);
          return loadSessions();
        })
        .then(() => setCheckingAuth(false))
        .catch(() => {
          localStorage.removeItem("auth_token");
          localStorage.removeItem("auth_email");
          setUser(null);
          setCheckingAuth(false);
        });
    } else {
      setCheckingAuth(false);
    }
  }, [loadSessions]);

  useEffect(() => {
    const el = messagesRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages]);

  useEffect(() => {
    return () => {
      abortControllerRef.current?.abort();
    };
  }, []);

  const onStop = () => {
    abortControllerRef.current?.abort();
    abortControllerRef.current = null;
    setBusy(false);
  };

  // Create new session
  const handleNewSession = async () => {
    try {
      const session = await createSession();
      setSessions((prev) => [session, ...prev]);
      setCurrentSessionId(session.id);
      setMessages([]);
      setSidebarOpen(false);
      setError("");
    } catch (err) {
      setError(err.message);
    }
  };

  // Select a session
  const handleSelectSession = (sessionId) => {
    if (busy) return;
    setCurrentSessionId(sessionId);
    loadMessages(sessionId);
    setSidebarOpen(false);
    setError("");
  };

  // Delete a session
  const handleDeleteSession = async (sessionId) => {
    try {
      await deleteSession(sessionId);
      setSessions((prev) => prev.filter((s) => s.id !== sessionId));
      if (currentSessionId === sessionId) {
        setCurrentSessionId(null);
        setMessages([]);
      }
    } catch (err) {
      setError(err.message);
    }
  };

  // Handle title update from stream
  const handleTitle = useCallback((title) => {
    setSessions((prev) =>
      prev.map((s) => (s.id === currentSessionId ? { ...s, title } : s))
    );
  }, [currentSessionId]);

  // Submit message
  const onSubmit = async (event, inputRef) => {
    event.preventDefault();
    const cleaned = text.trim();
    if (!cleaned || busy) return;

    setError("");

    // If no current session, create one first
    let sessionId = currentSessionId;
    if (!sessionId) {
      try {
        const session = await createSession();
        setSessions((prev) => [session, ...prev]);
        sessionId = session.id;
        setCurrentSessionId(session.id);
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
        session_id: sessionId,
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
        onTitle: handleTitle,
      });

      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === assistantMessageId && !msg.content.trim()
            ? { ...msg, content: "Nao foi possivel obter resposta do modelo agora." }
            : msg
        )
      );
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
      abortControllerRef.current = null;
      setBusy(false);
    }
  };

  const handleLogout = async () => {
    try { await logoutUser(); } catch { }
    localStorage.removeItem("auth_token");
    localStorage.removeItem("auth_email");
    setUser(null);
    setSessions([]);
    setCurrentSessionId(null);
    setMessages([]);
  };

  const handleAuthSuccess = (email) => {
    setUser(email);
    loadSessions();
  };

  if (checkingAuth) {
    return (
      <main className="app-shell">
        <div className="auth-screen">
          <div className="auth-card">
            <p className="auth-subtitle">Verificando autenticacao...</p>
          </div>
        </div>
      </main>
    );
  }

  if (!user) {
    return (
      <main className="app-shell">
        <AuthScreen onAuthSuccess={handleAuthSuccess} />
      </main>
    );
  }

  return (
    <div className="app-layout">
      <Sidebar
        sessions={sessions}
        currentSessionId={currentSessionId}
        onSelectSession={handleSelectSession}
        onNewSession={handleNewSession}
        onDeleteSession={handleDeleteSession}
        onToggle={() => setSidebarOpen(!sidebarOpen)}
        open={sidebarOpen}
      />

      <main className="app-shell">
        <header className="app-header">
          <span className="header-left">
            <button className="sidebar-toggle" onClick={() => setSidebarOpen(!sidebarOpen)} title="Sessoes">
              <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round">
                <line x1="3" y1="5" x2="17" y2="5" /><line x1="3" y1="10" x2="17" y2="10" /><line x1="3" y1="15" x2="17" y2="15" />
              </svg>
            </button>
            <span className="brand">ChatLLM Lab</span>
          </span>
          <span className="header-right">
            <span className="user-email">{user}</span>
            <button className="logout-btn" onClick={handleLogout} title="Sair">Sair</button>
          </span>
        </header>

        <section className="messages" aria-live="polite" ref={messagesRef}>
          <div className="messages-inner">
            {loadingMessages && <p className="note">Carregando mensagens...</p>}
            {!loadingMessages && messages.length === 0 && (
              <p className="note" style={{ textAlign: "center", marginTop: 60, color: "var(--muted)" }}>
                Inicie uma nova conversa ou selecione uma sessao existente.
              </p>
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

