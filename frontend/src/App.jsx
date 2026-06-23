const { useEffect, useMemo, useRef, useState, useCallback } = React;

function createMessageId() {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

function App() {
  const [user, setUser] = useState(null);
  const [loadingAuth, setLoadingAuth] = useState(true);
  const [sessions, setSessions] = useState([]);
  const [currentSessionId, setCurrentSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const messagesRef = useRef(null);
  const abortControllerRef = useRef(null);
  const latestSessionIdRef = useRef(null);

  const loadSessions = useCallback(async () => {
    try {
      const data = await listSessions();
      setSessions(data.sessions || []);
    } catch { /* ignore */ }
  }, []);

  const loadSessionMessages = useCallback(async (sessionId) => {
    try {
      const msgs = await getSessionMessages(sessionId);
      const formatted = msgs.map((m) => ({
        id: createMessageId(),
        role: m.role,
        content: m.content,
      }));
      setMessages(formatted);
      setCurrentSessionId(sessionId);
    } catch (err) {
      setError(err.message);
    }
  }, []);

  useEffect(() => {
    checkAuth().then(async (data) => {
      if (data) {
        setUser(data);
        await loadSessions();
      }
      setLoadingAuth(false);
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

  const handleAuth = async (data) => {
    setUser({ email: data.email, user_id: data.user_id });
    await loadSessions();
  };

  const handleLogout = async () => {
    await logout();
    setUser(null);
    setSessions([]);
    setMessages([]);
    setCurrentSessionId(null);
    setError("");
  };

  const handleNewSession = async () => {
    try {
      const session = await createSession();
      setCurrentSessionId(session.id);
      setMessages([{
        id: createMessageId(),
        role: "assistant",
        content: "Nova conversa iniciada. Como posso ajudar?",
      }]);
      await loadSessions();
    } catch (err) {
      setError(err.message);
    }
  };

  const handleSelectSession = async (sessionId) => {
    if (busy) return;
    abortControllerRef.current?.abort();
    abortControllerRef.current = null;
    setBusy(false);
    await loadSessionMessages(sessionId);
  };

  const handleDeleteSession = async (sessionId) => {
    try {
      await deleteSession(sessionId);
      if (currentSessionId === sessionId) {
        setCurrentSessionId(null);
        setMessages([]);
      }
      await loadSessions();
    } catch (err) {
      setError(err.message);
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
    latestSessionIdRef.current = null;
    const abortController = new AbortController();
    abortControllerRef.current = abortController;

    try {
      const resolvedSessionId = await sendMessageStream({
        message: cleaned,
        history: chatHistory,
        sessionId: currentSessionId,
        signal: abortController.signal,
        onDelta: (delta, sid) => {
          if (sid && latestSessionIdRef.current === null) {
            latestSessionIdRef.current = sid;
          }
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === assistantMessageId
                ? { ...msg, content: `${msg.content}${delta}` }
                : msg
            )
          );
        },
      });

      if (resolvedSessionId && resolvedSessionId !== currentSessionId) {
        setCurrentSessionId(resolvedSessionId);
      }

      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === assistantMessageId && !msg.content.trim()
            ? { ...msg, content: "Nao foi possivel obter resposta do modelo agora." }
            : msg
        )
      );

      await loadSessions();
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
    return <main className="auth-shell"><div className="auth-card" style={{ textAlign: "center" }}>Carregando...</div></main>;
  }

  if (!user) {
    return <AuthScreen onAuth={handleAuth} />;
  }

  return (
    <main className="app-shell with-sidebar">
      <Sidebar
        sessions={sessions}
        currentSessionId={currentSessionId}
        onSelectSession={handleSelectSession}
        onNewSession={handleNewSession}
        onDeleteSession={handleDeleteSession}
      />
      <div className="chat-area">
        <header className="app-header">
          <div className="brand">ChatLLM Lab</div>
          <div className="header-right">
            <span className="header-email">{user.email}</span>
            <button className="btn-logout" onClick={handleLogout}>Sair</button>
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
      </div>
    </main>
  );
}

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(<App />);

