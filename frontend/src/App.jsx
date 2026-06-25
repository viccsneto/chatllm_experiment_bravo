const { useEffect, useMemo, useRef, useState, useCallback } = React;

function createMessageId() {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

function ChatApp({ user, onLogout }) {
  const [sessions, setSessions] = useState([]);
  const [currentSessionId, setCurrentSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [loadingSessions, setLoadingSessions] = useState(true);
  const messagesRef = useRef(null);
  const abortControllerRef = useRef(null);
  const initialLoadRef = useRef(true);

  // Load sessions on mount
  useEffect(() => {
    fetchSessions().then((s) => {
      setSessions(s);
      if (s.length > 0) {
        setCurrentSessionId(s[0].id);
      }
      setLoadingSessions(false);
    }).catch(() => {
      setLoadingSessions(false);
    });
  }, []);

  // Load messages when currentSessionId changes
  useEffect(() => {
    if (!currentSessionId) {
      setMessages([]);
      return;
    }
    // Fetch messages for this session (initial load only, not on every render)
    if (initialLoadRef.current || !messages.length) {
      // Messages will be loaded from history on first send
      // For now, reset local messages on session switch
      setMessages([]);
    }
    initialLoadRef.current = false;
  }, [currentSessionId]);

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

  const refreshSessions = useCallback(async () => {
    try {
      const s = await fetchSessions();
      setSessions(s);
    } catch {}
  }, []);

  const handleSelectSession = useCallback((sessionId) => {
    abortControllerRef.current?.abort();
    setBusy(false);
    setError("");
    setCurrentSessionId(sessionId);
  }, []);

  const handleCreateSession = useCallback(async () => {
    try {
      const s = await createSession();
      setSessions((prev) => [s, ...prev]);
      setCurrentSessionId(s.id);
    } catch (err) {
      setError(err.message);
    }
  }, []);

  const handleDeleteSession = useCallback(async (sessionId) => {
    try {
      await deleteSession(sessionId);
      setSessions((prev) => prev.filter((s) => s.id !== sessionId));
      if (currentSessionId === sessionId) {
        setCurrentSessionId((prev) => {
          const remaining = sessions.filter((s) => s.id !== sessionId);
          return remaining.length > 0 ? remaining[0].id : null;
        });
      }
    } catch (err) {
      setError(err.message);
    }
  }, [currentSessionId, sessions]);

  const onStop = () => {
    abortControllerRef.current?.abort();
    abortControllerRef.current = null;
    setBusy(false);
  };

  const onSubmit = async (event, inputRef) => {
    event.preventDefault();
    const cleaned = text.trim();
    if (!cleaned || busy) return;

    // Ensure we have a session
    let sessionId = currentSessionId;
    if (!sessionId) {
      try {
        const s = await createSession();
        setSessions((prev) => [s, ...prev]);
        sessionId = s.id;
        setCurrentSessionId(s.id);
      } catch (err) {
        setError(err.message);
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
        session_id: sessionId,
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
      refreshSessions(); // Refresh to get updated titles
    }
  };

  const handleLogoutClick = async () => {
    await logout();
    onLogout();
  };

  return (
    <main className="app-shell app-shell-with-sidebar">
      <Sidebar
        sessions={sessions}
        currentSessionId={currentSessionId}
        onSelect={handleSelectSession}
        onCreate={handleCreateSession}
        onDelete={handleDeleteSession}
        loading={loadingSessions}
      />

      <div className="main-area">
        <header className="app-header">
          <div className="brand">ChatLLM Lab</div>
          <div className="header-right">
            <span className="user-email">{user.email}</span>
            <button className="logout-btn" onClick={handleLogoutClick} title="Sair">
              Sair
            </button>
          </div>
        </header>

        <section className="messages" aria-live="polite" ref={messagesRef}>
          <div className="messages-inner">
            {!currentSessionId && !loadingSessions && (
              <div className="welcome-placeholder">
                <p>Crie uma nova sessao para comecar.</p>
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
      </div>
    </main>
  );
}

function AppWrapper() {
  const [user, setUser] = useState(null);
  const [checking, setChecking] = useState(true);

  useEffect(() => {
    if (isAuthenticated()) {
      fetchMe().then((me) => {
        if (me) setUser(me);
        setChecking(false);
      }).catch(() => setChecking(false));
    } else {
      setChecking(false);
    }
  }, []);

  const handleAuthSuccess = useCallback((me) => setUser(me), []);
  const handleLogout = useCallback(() => setUser(null), []);

  if (checking) {
    return (
      <main className="app-shell">
        <div className="loading-screen">Carregando...</div>
      </main>
    );
  }

  if (!user) {
    return <AuthScreen onAuthSuccess={handleAuthSuccess} />;
  }

  return <ChatApp user={user} onLogout={handleLogout} />;
}

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(<AppWrapper />);

