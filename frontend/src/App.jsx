const { useEffect, useMemo, useRef, useState, useCallback } = React;

function createMessageId() {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

function LoginScreen({ onAuth }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isSignup, setIsSignup] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      if (isSignup) {
        await apiSignup(email, password);
      } else {
        await apiLogin(email, password);
      }
      onAuth();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="app-shell">
      <div className="auth-container">
        <div className="auth-box">
          <h1 className="auth-title">ChatLLM Lab</h1>
          <p className="auth-subtitle">{isSignup ? "Criar conta" : "Entrar"}</p>
          {error && <div className="error" style={{ textAlign: "center", marginBottom: 12 }}>{error}</div>}
          <form onSubmit={handleSubmit} className="auth-form">
            <input
              type="email"
              placeholder="Email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoFocus
            />
            <input
              type="password"
              placeholder="Senha"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={4}
            />
            <button type="submit" disabled={loading}>
              {loading ? "Aguarde..." : isSignup ? "Cadastrar" : "Entrar"}
            </button>
          </form>
          <p className="auth-toggle">
            {isSignup ? "Ja tem conta?" : "Nao tem conta?"}{" "}
            <a href="#" onClick={(e) => { e.preventDefault(); setIsSignup(!isSignup); setError(""); }}>
              {isSignup ? "Entrar" : "Cadastrar"}
            </a>
          </p>
        </div>
      </div>
    </main>
  );
}

function Sidebar({ sessions, activeSessionId, onSelect, onNew, onDelete, open }) {
  return (
    <div className={`sidebar ${open ? "sidebar--open" : ""}`}>
      <div className="sidebar-header">
        <span className="brand">ChatLLM Lab</span>
      </div>
      <button className="sidebar-new-btn" onClick={onNew}>
        + Nova conversa
      </button>
      <div className="sidebar-list">
        {sessions.map((s) => (
          <div
            key={`${s.id}-${s.title}`}
            className={`sidebar-item ${s.id === activeSessionId ? "sidebar-item--active" : ""}`}
            onClick={() => onSelect(s.id)}
          >
            <span className="sidebar-item-title">{s.title || "Nova conversa"}</span>
            <button
              className="sidebar-item-del"
              onClick={(e) => { e.stopPropagation(); onDelete(s.id); }}
              title="Deletar"
            >
              ×
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}

const WELCOME_MSG = {
  id: createMessageId(),
  role: "assistant",
  content: "Bem-vindo ao ChatLLM Lab. Como posso ajudar voce hoje?",
};

function App() {
  const [user, setUser] = useState(null);
  const [checking, setChecking] = useState(true);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [sessions, setSessions] = useState([]);
  const [activeSessionId, setActiveSessionId] = useState(null);
  const [messages, setMessages] = useState([WELCOME_MSG]);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const messagesRef = useRef(null);
  const abortControllerRef = useRef(null);

  const updateSidebarTitle = useCallback((sessionId, newTitle) => {
    setSessions((prev) =>
      prev.map((s) => (s.id === sessionId ? { ...s, title: newTitle } : s))
    );
  }, []);

  const loadSessions = useCallback(async () => {
    try {
      const data = await apiListSessions();
      setSessions(data.sessions || []);
    } catch (e) {
      // Silencia erro ao listar sessoes
    }
  }, []);

  useEffect(() => {
    apiMe().then((data) => {
      if (data) {
        setUser(data);
        loadSessions();
      }
      setChecking(false);
    });
  }, [loadSessions]);

  const chatHistory = useMemo(
    () => messages.filter((msg) => msg.role === "user" || msg.role === "assistant"),
    [messages]
  );

  useEffect(() => {
    const el = messagesRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages]);

  useEffect(() => {
    return () => {
      abortControllerRef.current?.abort();
    };
  }, []);

  const switchSession = async (sessionId) => {
    abortControllerRef.current?.abort();
    setActiveSessionId(sessionId);
    setBusy(false);
    try {
      const data = await apiGetSessionMessages(sessionId);
      const msgs = (data.messages || []).map((m) => ({
        id: createMessageId(),
        role: m.role,
        content: m.content,
      }));
      setMessages(msgs.length ? msgs : [WELCOME_MSG]);
    } catch {
      setMessages([WELCOME_MSG]);
    }
  };

  const handleNewSession = async () => {
    abortControllerRef.current?.abort();
    try {
      const session = await apiCreateSession();
      setSessions((prev) => [session, ...prev]);
      setActiveSessionId(session.id);
      setMessages([WELCOME_MSG]);
      setSidebarOpen(false);
    } catch (e) {
      setError("Erro ao criar sessao");
    }
  };

  const handleDeleteSession = async (sessionId) => {
    try {
      await apiDeleteSession(sessionId);
      setSessions((prev) => prev.filter((s) => s.id !== sessionId));
      if (activeSessionId === sessionId) {
        setActiveSessionId(null);
        setMessages([WELCOME_MSG]);
      }
    } catch {
      setError("Erro ao deletar sessao");
    }
  };

  const onStop = () => {
    abortControllerRef.current?.abort();
    abortControllerRef.current = null;
    setBusy(false);
  };

  const onSubmit = async (event, inputRef) => {
    event.preventDefault();
    const cleaned = text.trim();
    if (!cleaned || busy) return;

    let sessionId = activeSessionId;
    if (!sessionId) {
      try {
        const session = await apiCreateSession();
        setSessions((prev) => [session, ...prev]);
        sessionId = session.id;
        setActiveSessionId(session.id);
      } catch {
        setError("Erro ao criar sessao");
        return;
      }
    }

    setError("");
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
        sessionId,
        history: chatHistory,
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
        onDone: (payload) => {
          if (payload.title) {
            updateSidebarTitle(payload.session_id, payload.title);
          }
        },
      });

      // Poll ate o titulo ser gerado (max 10 tentativas)
      for (let i = 0; i < 10; i++) {
        const data = await apiListSessions();
        const active = (data.sessions || []).find((s) => s.id === sessionId);
        if (active && active.title !== "Nova conversa") {
          updateSidebarTitle(sessionId, active.title);
          break;
        }
        await new Promise((r) => setTimeout(r, 500));
      }

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
    await apiLogout();
    setUser(null);
    setSessions([]);
    setActiveSessionId(null);
    setMessages([WELCOME_MSG]);
  };

  if (checking) {
    return (
      <main className="app-shell">
        <div className="auth-container">
          <div className="auth-box">
            <p style={{ textAlign: "center", color: "var(--muted)" }}>Carregando...</p>
          </div>
        </div>
      </main>
    );
  }

  if (!user) {
    return <LoginScreen onAuth={() => apiMe().then(setUser)} />;
  }

  return (
    <div className="app-layout">
      <Sidebar
        sessions={sessions}
        activeSessionId={activeSessionId}
        onSelect={switchSession}
        onNew={handleNewSession}
        onDelete={handleDeleteSession}
        open={sidebarOpen}
      />

      <main className="app-shell">
        <header className="app-header">
          <button className="sidebar-toggle" onClick={() => setSidebarOpen((v) => !v)}>
            ☰
          </button>
          <div className="brand">ChatLLM Lab</div>
          <div className="header-right">
            <span className="user-email">{user.email}</span>
            <button className="logout-btn" onClick={handleLogout}>Sair</button>
          </div>
        </header>

        <section className="messages" aria-live="polite" ref={messagesRef}>
          <div className="messages-inner">
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

