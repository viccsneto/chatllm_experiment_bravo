const { useCallback, useEffect, useMemo, useRef, useState } = React;

function createMessageId() {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

/* ── Tela de login / cadastro ──────────────────── */

function AuthPage({ onAuthSuccess }) {
  const [mode, setMode] = useState("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      if (mode === "login") {
        await apiLogin(email, password);
      } else {
        await apiSignup(email, password);
      }
      onAuthSuccess();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const toggleMode = () => {
    setMode((m) => (m === "login" ? "signup" : "login"));
    setError("");
  };

  return (
    <div className="auth-page">
      <div className="auth-card">
        <h1 className="auth-title">ChatLLM Lab</h1>
        <p className="auth-subtitle">
          {mode === "login" ? "Entre com sua conta" : "Crie sua conta"}
        </p>
        {error && <div className="auth-error">{error}</div>}
        <form onSubmit={handleSubmit} className="auth-form">
          <input type="email" placeholder="Email" value={email} onChange={(e) => setEmail(e.target.value)} required autoFocus />
          <input type="password" placeholder="Senha (min. 8 caracteres)" value={password} onChange={(e) => setPassword(e.target.value)} required minLength={mode === "signup" ? 8 : 1} />
          <button type="submit" disabled={loading}>{loading ? "Aguarde..." : mode === "login" ? "Entrar" : "Criar conta"}</button>
        </form>
        <p className="auth-toggle">
          {mode === "login" ? (
            <>Nao tem conta? <button className="link-btn" onClick={toggleMode}>Cadastre-se</button></>
          ) : (
            <>Ja tem conta? <button className="link-btn" onClick={toggleMode}>Fazer login</button></>
          )}
        </p>
      </div>
    </div>
  );
}

/* ── Chat com sessoes ─────────────────────────── */

function ChatApp({ userEmail, onLogout }) {
  const [sessions, setSessions] = useState([]);
  const [activeSessionId, setActiveSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [sidebarLoading, setSidebarLoading] = useState(true);
  const [messagesLoading, setMessagesLoading] = useState(false);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [loggingOut, setLoggingOut] = useState(false);
  const messagesRef = useRef(null);
  const abortControllerRef = useRef(null);

  const chatHistory = useMemo(
    () => messages.filter((msg) => msg.role === "user" || msg.role === "assistant"),
    [messages]
  );

  useEffect(() => {
    const el = messagesRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages]);

  useEffect(() => {
    return () => { abortControllerRef.current?.abort(); };
  }, []);

  // Carrega sessoes ao montar
  const loadSessions = useCallback(async () => {
    try {
      const data = await apiListSessions();
      setSessions(data.sessions);
      if (data.sessions.length > 0 && !activeSessionId) {
        setActiveSessionId(data.sessions[0].id);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setSidebarLoading(false);
    }
  }, []);

  useEffect(() => {
    loadSessions();
  }, [loadSessions]);

  // Carrega mensagens ao trocar de sessao
  useEffect(() => {
    if (!activeSessionId) {
      setMessages([]);
      return;
    }
    setMessagesLoading(true);
    setError("");
    apiGetSessionMessages(activeSessionId)
      .then((data) => {
        const formatted = data.messages.map((m, i) => ({
          id: `${activeSessionId}-${i}-${Date.now()}`,
          role: m.role,
          content: m.content,
        }));
        setMessages(formatted.length > 0 ? formatted : [
          { id: createMessageId(), role: "assistant", content: "Bem-vindo ao ChatLLM Lab. Como posso ajudar voce hoje?" },
        ]);
      })
      .catch((err) => setError(err.message))
      .finally(() => setMessagesLoading(false));
  }, [activeSessionId]);

  const onStop = () => {
    abortControllerRef.current?.abort();
    abortControllerRef.current = null;
    setBusy(false);
  };

  const onSubmit = async (event) => {
    event.preventDefault();
    const cleaned = text.trim();
    if (!cleaned || busy || !activeSessionId) return;

    setError("");
    const userMessage = { id: createMessageId(), role: "user", content: cleaned };
    const assistantMessageId = createMessageId();

    setMessages((prev) => [...prev, userMessage, { id: assistantMessageId, role: "assistant", content: "" }]);
    setText("");
    setBusy(true);
    const abortController = new AbortController();
    abortControllerRef.current = abortController;

    try {
      await sendMessageStream({
        message: cleaned,
        sessionId: activeSessionId,
        history: chatHistory,
        signal: abortController.signal,
        onDelta: (delta) => {
          setMessages((prev) =>
            prev.map((msg) => msg.id === assistantMessageId ? { ...msg, content: `${msg.content}${delta}` } : msg)
          );
        },
        onDone: (payload) => {
          // Atualiza titulo se veio no evento done
          if (payload.title) {
            setSessions((prev) =>
              prev.map((s) => s.id === activeSessionId ? { ...s, title: payload.title } : s)
            );
          }
        },
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

  const handleCreateSession = async () => {
    if (busy) return;
    setError("");
    try {
      const newSession = await apiCreateSession();
      setSessions((prev) => [newSession, ...prev]);
      setActiveSessionId(newSession.id);
    } catch (err) {
      setError(err.message);
    }
  };

  const handleSelectSession = (sessionId) => {
    if (busy) {
      onStop();
    }
    setActiveSessionId(sessionId);
  };

  const handleLogout = async () => {
    setLoggingOut(true);
    try {
      await apiLogout();
      onLogout();
    } catch (err) {
      setError(err.message);
      setLoggingOut(false);
    }
  };

  return (
    <div className="app-layout">
      <Sidebar
        sessions={sessions}
        activeSessionId={activeSessionId}
        onSelectSession={handleSelectSession}
        onCreateSession={handleCreateSession}
        loading={sidebarLoading}
      />

      <main className="app-main">
        <header className="app-header">
          <div className="brand">ChatLLM Lab</div>
          <div className="header-user">
            <span className="header-email" title={userEmail}>{userEmail}</span>
            <button className="logout-btn" onClick={handleLogout} disabled={loggingOut}>
              {loggingOut ? "Saindo..." : "Sair"}
            </button>
          </div>
        </header>

        <section className="messages" aria-live="polite" ref={messagesRef}>
          <div className="messages-inner">
            {messagesLoading && <div className="messages-loading">Carregando mensagens...</div>}
            {!messagesLoading && messages.map((msg) => (
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

/* ── App raiz ──────────────────────────────────── */

function App() {
  const [user, setUser] = useState(null);
  const [initialLoading, setInitialLoading] = useState(true);

  useEffect(() => {
    apiMe().then((data) => setUser(data ? { email: data.email } : false))
      .catch(() => setUser(false))
      .finally(() => setInitialLoading(false));
  }, []);

  if (initialLoading) {
    return (
      <div className="auth-page">
        <div className="auth-card"><p className="auth-subtitle">Carregando...</p></div>
      </div>
    );
  }

  if (!user) {
    return <AuthPage onAuthSuccess={() => {
      apiMe().then((data) => setUser(data ? { email: data.email } : false));
    }} />;
  }

  return <ChatApp userEmail={user.email} onLogout={() => setUser(false)} />;
}

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(<App />);

