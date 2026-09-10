const { useEffect, useMemo, useRef, useState } = React;

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

function App() {
  const [user, setUser] = useState(null);
  const [authLoading, setAuthLoading] = useState(true);
  const [authBusy, setAuthBusy] = useState(false);
  const [authMode, setAuthMode] = useState("login");
  const [authError, setAuthError] = useState("");
  const [messages, setMessages] = useState(createInitialMessages);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [logoutBusy, setLogoutBusy] = useState(false);
  const [error, setError] = useState("");
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

    try {
      await sendMessageStream({
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

      <div className="warning-banner">Lembre-se, você precisa focar no experimento!!!</div>
    </main>
  );
}

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(<App />);
