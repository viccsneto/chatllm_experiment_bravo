const { useEffect, useRef, useState } = React;

function createMessageId() {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

function createInitialMessages() {
  return [
    {
      id: createMessageId(),
      role: "assistant",
      content: "Bem-vindo ao ChatLLM Lab. Como posso ajudar voce hoje?",
    },
  ];
}

function messagesFromSession(storedMessages) {
  if (!storedMessages?.length) return createInitialMessages();
  return storedMessages.map((message) => ({
    id: `stored-${message.id}`,
    role: message.role,
    content: message.content,
  }));
}

function App() {
  const [user, setUser] = useState(null);
  const [authLoading, setAuthLoading] = useState(true);
  const [authBusy, setAuthBusy] = useState(false);
  const [authMode, setAuthMode] = useState("login");
  const [authError, setAuthError] = useState("");
  const [messages, setMessages] = useState(createInitialMessages);
  const [sessions, setSessions] = useState([]);
  const [activeSessionId, setActiveSessionId] = useState(null);
  const [sessionsLoading, setSessionsLoading] = useState(false);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [logoutBusy, setLogoutBusy] = useState(false);
  const [error, setError] = useState("");
  const messagesRef = useRef(null);
  const abortControllerRef = useRef(null);

  useEffect(() => {
    const el = messagesRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages]);

  useEffect(() => {
    let active = true;
    getCurrentUser()
      .then((currentUser) => {
        if (active) setUser(currentUser);
      })
      .catch((err) => {
        if (active) setAuthError(err.message || "Falha ao verificar a autenticacao.");
      })
      .finally(() => {
        if (active) setAuthLoading(false);
      });

    return () => {
      active = false;
      abortControllerRef.current?.abort();
    };
  }, []);

  useEffect(() => {
    if (!user) return undefined;

    let active = true;
    const loadSessions = async () => {
      setSessionsLoading(true);
      setError("");
      try {
        let availableSessions = await listChatSessions();
        if (!active) return;

        if (availableSessions.length === 0) {
          const created = await createChatSession();
          availableSessions = [created];
        }
        if (!active) return;

        const selected = availableSessions[0];
        const detail = await getChatSession(selected.id);
        if (!active) return;

        setSessions(availableSessions);
        setActiveSessionId(selected.id);
        setMessages(messagesFromSession(detail.messages));
      } catch (err) {
        if (active) setError(err.message || "Nao foi possivel carregar as conversas.");
      } finally {
        if (active) setSessionsLoading(false);
      }
    };

    loadSessions();
    return () => {
      active = false;
    };
  }, [user]);

  const onAuthenticate = async (credentials) => {
    setAuthBusy(true);
    setAuthError("");
    try {
      const authenticatedUser = authMode === "register"
        ? await registerUser(credentials)
        : await loginUser(credentials);
      setUser(authenticatedUser);
    } catch (err) {
      setAuthError(err.message || "Nao foi possivel autenticar.");
    } finally {
      setAuthBusy(false);
    }
  };

  const onChangeAuthMode = (mode) => {
    setAuthMode(mode);
    setAuthError("");
  };

  const onLogout = async () => {
    setLogoutBusy(true);
    setError("");
    abortControllerRef.current?.abort();
    try {
      await logoutUser();
      setUser(null);
      setSessions([]);
      setActiveSessionId(null);
      setMessages(createInitialMessages());
      setText("");
    } catch (err) {
      setError(err.message || "Nao foi possivel sair.");
    } finally {
      setLogoutBusy(false);
    }
  };

  const onStop = () => {
    abortControllerRef.current?.abort();
    abortControllerRef.current = null;
    setBusy(false);
  };

  const onNewSession = async () => {
    if (busy || sessionsLoading) return;
    setSessionsLoading(true);
    setError("");
    try {
      const created = await createChatSession();
      setSessions((current) => [created, ...current]);
      setActiveSessionId(created.id);
      setMessages(createInitialMessages());
      setText("");
    } catch (err) {
      setError(err.message || "Nao foi possivel criar a conversa.");
    } finally {
      setSessionsLoading(false);
    }
  };

  const onSelectSession = async (sessionId) => {
    if (busy || sessionsLoading || sessionId === activeSessionId) return;
    setSessionsLoading(true);
    setError("");
    try {
      const detail = await getChatSession(sessionId);
      setActiveSessionId(sessionId);
      setMessages(messagesFromSession(detail.messages));
      setText("");
    } catch (err) {
      setError(err.message || "Nao foi possivel carregar a conversa.");
    } finally {
      setSessionsLoading(false);
    }
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
    let completedSession = null;

    try {
      await sendMessageStream({
        message: cleaned,
        sessionId: activeSessionId,
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
          completedSession = payload;
          setActiveSessionId(payload.session_id);
        },
      });

      if (completedSession) {
        const refreshedSessions = await listChatSessions();
        setSessions(refreshedSessions);
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

  if (authLoading) {
    return (
      <main className="auth-shell">
        <div className="auth-loading">Carregando...</div>
      </main>
    );
  }

  if (!user) {
    return (
      <AuthForm
        mode={authMode}
        busy={authBusy}
        error={authError}
        onChangeMode={onChangeAuthMode}
        onSubmit={onAuthenticate}
      />
    );
  }

  return (
    <main className="app-shell">
      <header className="app-header">
        <div aria-hidden="true" />
        <div className="brand">ChatLLM Lab</div>
        <div className="header-user">
          <span title={user.email}>{user.email}</span>
          <button type="button" onClick={onLogout} disabled={logoutBusy}>
            {logoutBusy ? "Saindo..." : "Sair"}
          </button>
        </div>
      </header>

      <div className="workspace">
        <Sidebar
          sessions={sessions}
          activeSessionId={activeSessionId}
          loading={sessionsLoading}
          disabled={busy}
          onNew={onNewSession}
          onSelect={onSelectSession}
        />

        <section className="chat-pane">
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
            disabled={sessionsLoading}
            error={error}
            onChangeText={setText}
            onSubmit={onSubmit}
            onStop={onStop}
          />
        </section>
      </div>

      <div className="warning-banner">Lembre-se, você precisa focar no experimento!!!</div>
    </main>
  );
}

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(<App />);
