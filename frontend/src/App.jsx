const { useEffect, useMemo, useRef, useState, useCallback } = React;

function createMessageId() {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

function App() {
  const [userEmail, setUserEmail] = useState(null);
  const [loadingAuth, setLoadingAuth] = useState(true);
  const [sessions, setSessions] = useState([]);
  const [activeSessionId, setActiveSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const messagesRef = useRef(null);
  const abortControllerRef = useRef(null);

  // Load user on mount
  useEffect(() => {
    apiMe().then((user) => {
      if (user) {
        setUserEmail(user.email);
        return loadSessions();
      }
    }).finally(() => setLoadingAuth(false));
  }, []);

  const loadSessions = async () => {
    try {
      const list = await apiListSessions();
      setSessions(list);
      if (list.length > 0 && !activeSessionId) {
        loadSession(list[0].id);
      }
    } catch {
      // silencia
    }
  };

  const loadSession = async (sessionId) => {
    try {
      const session = await apiGetSession(sessionId);
      setActiveSessionId(session.id);
      const loaded = (session.messages || []).map((msg) => ({
        id: createMessageId(),
        role: msg.role,
        content: msg.content,
      }));
      if (loaded.length === 0) {
        loaded.push({
          id: createMessageId(),
          role: "assistant",
          content: "Bem-vindo ao ChatLLM Lab. Como posso ajudar voce hoje?",
        });
      }
      setMessages(loaded);
    } catch {
      setError("Erro ao carregar sessao.");
    }
  };

  const refreshSessionList = useCallback(async () => {
    try {
      const list = await apiListSessions();
      setSessions(list);
    } catch {
      // silencia
    }
  }, []);

  const handleAuth = (email) => {
    setUserEmail(email);
    loadSessions();
  };

  const handleLogout = async () => {
    try {
      await apiAuth("logout", {});
    } catch { /* ok */ }
    clearToken();
    setUserEmail(null);
    setSessions([]);
    setActiveSessionId(null);
    setMessages([]);
  };

  const handleCreateSession = async () => {
    try {
      const session = await apiCreateSession();
      setActiveSessionId(session.id);
      setMessages([{
        id: createMessageId(),
        role: "assistant",
        content: "Bem-vindo ao ChatLLM Lab. Como posso ajudar voce hoje?",
      }]);
      await refreshSessionList();
    } catch (err) {
      setError(err.message);
    }
  };

  const handleDeleteSession = async (sessionId) => {
    try {
      await apiDeleteSession(sessionId);
      if (activeSessionId === sessionId) {
        setActiveSessionId(null);
        setMessages([]);
      }
      await refreshSessionList();
    } catch (err) {
      setError(err.message);
    }
  };

  const handleSelectSession = (sessionId) => {
    if (sessionId === activeSessionId) return;
    loadSession(sessionId);
  };

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

  const onStop = () => {
    abortControllerRef.current?.abort();
    abortControllerRef.current = null;
    setBusy(false);
  };

  const onSubmit = async (event, inputRef) => {
    event.preventDefault();
    const cleaned = text.trim();
    if (!cleaned || busy) return;

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

    let resultSessionId = activeSessionId;

    try {
      resultSessionId = await sendMessageStream({
        message: cleaned,
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
        sessionId: activeSessionId,
      });

      // Atualiza sidebar e estado da sessao
      if (resultSessionId) {
        setActiveSessionId(resultSessionId);
      }
      await refreshSessionList();

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

  if (loadingAuth) {
    return (
      <main className="app-shell">
        <div className="auth-container">
          <div className="auth-card">
            <p style={{ textAlign: "center", color: "var(--muted)" }}>Carregando...</p>
          </div>
        </div>
      </main>
    );
  }

  if (!userEmail) {
    return <Auth onAuth={handleAuth} />;
  }

  return (
    <div className="app-layout">
      {sidebarOpen && (
        <Sidebar
          sessions={sessions}
          activeSessionId={activeSessionId}
          onSelectSession={handleSelectSession}
          onCreateSession={handleCreateSession}
          onDeleteSession={handleDeleteSession}
        />
      )}

      <main className="app-main">
        <header className="app-header">
          <div className="header-left">
            <button
              type="button"
              className="sidebar-toggle"
              onClick={() => setSidebarOpen((prev) => !prev)}
              aria-label="Alternar sidebar"
            >
              <svg width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true">
                <line x1="3" y1="4" x2="15" y2="4" />
                <line x1="3" y1="9" x2="15" y2="9" />
                <line x1="3" y1="14" x2="15" y2="14" />
              </svg>
            </button>
            <span className="brand">ChatLLM Lab</span>
          </div>
          <div className="header-right">
            <span className="header-email">{userEmail}</span>
            <button type="button" className="logout-btn" onClick={handleLogout}>
              Sair
            </button>
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
      </main>
    </div>
  );
}

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(<App />);

