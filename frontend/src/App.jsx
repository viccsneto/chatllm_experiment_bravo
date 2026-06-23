const { useEffect, useMemo, useRef, useState, useCallback } = React;

function createMessageId() {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

function App() {
  const [user, setUser] = useState(() => {
    const token = localStorage.getItem("access_token");
    const email = localStorage.getItem("user_email");
    return token ? { token, email } : null;
  });
  const [sessions, setSessions] = useState([]);
  const [activeSessionId, setActiveSessionId] = useState(null);
  const [messages, setMessages] = useState([
    {
      id: createMessageId(),
      role: "assistant",
      content: "Bem-vindo ao ChatLLM Lab. Como posso ajudar voce hoje?",
    },
  ]);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const messagesRef = useRef(null);
  const abortControllerRef = useRef(null);
  const sessionsLoadedRef = useRef(false);

  const chatHistory = useMemo(
    () => messages.filter((msg) => msg.role === "user" || msg.role === "assistant"),
    [messages]
  );

  // Carregar sessoes ao logar
  useEffect(() => {
    if (!user || sessionsLoadedRef.current) return;
    sessionsLoadedRef.current = true;
    listSessions()
      .then((s) => {
        setSessions(s);
        if (s.length > 0) {
          setActiveSessionId(s[0].id);
          loadSessionMessages(s[0].id);
        } else {
          createSessionAndSelect();
        }
      })
      .catch(() => {});
  }, [user]);

  const loadSessionMessages = useCallback(async (sessionId) => {
    try {
      const msgs = await fetchSessionMessages(sessionId);
      if (msgs.length === 0) {
        setMessages([{
          id: createMessageId(),
          role: "assistant",
          content: "Bem-vindo ao ChatLLM Lab. Como posso ajudar voce hoje?",
        }]);
      } else {
        setMessages(msgs.map((m) => ({ ...m, id: createMessageId() })));
      }
    } catch {
      setMessages([{
        id: createMessageId(),
        role: "assistant",
        content: "Bem-vindo ao ChatLLM Lab. Como posso ajudar voce hoje?",
      }]);
    }
  }, []);

  const createSessionAndSelect = useCallback(async () => {
    try {
      const s = await createSession();
      setSessions((prev) => [s, ...prev]);
      setActiveSessionId(s.id);
      setMessages([{
        id: createMessageId(),
        role: "assistant",
        content: "Bem-vindo ao ChatLLM Lab. Como posso ajudar voce hoje?",
      }]);
    } catch {
      // silent
    }
  }, []);

  const selectSession = useCallback(async (sessionId) => {
    if (sessionId === activeSessionId) return;
    setActiveSessionId(sessionId);
    setMessages([]);
    loadSessionMessages(sessionId);
  }, [activeSessionId, loadSessionMessages]);

  const deleteSessionAndRefresh = useCallback(async (sessionId) => {
    try {
      await deleteSession(sessionId);
      const updated = sessions.filter((s) => s.id !== sessionId);
      setSessions(updated);
      if (activeSessionId === sessionId) {
        if (updated.length > 0) {
          setActiveSessionId(updated[0].id);
          loadSessionMessages(updated[0].id);
        } else {
          createSessionAndSelect();
        }
      }
    } catch {
      // silent
    }
  }, [sessions, activeSessionId, loadSessionMessages, createSessionAndSelect]);

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

    // Garantir que existe uma sessao ativa
    let sid = activeSessionId;
    if (!sid) {
      try {
        const s = await createSession();
        setSessions((prev) => [s, ...prev]);
        setActiveSessionId(s.id);
        sid = s.id;
      } catch {
        // fallback
      }
    }

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

      // Recarregar sessoes para pegar titulo atualizado
      listSessions().then(setSessions).catch(() => {});
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

  const handleAuth = (authUser) => {
    setUser(authUser);
  };

  const handleLogout = () => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("user_email");
    setUser(null);
    setSessions([]);
    setActiveSessionId(null);
    sessionsLoadedRef.current = false;
    setMessages([
      {
        id: createMessageId(),
        role: "assistant",
        content: "Bem-vindo ao ChatLLM Lab. Como posso ajudar voce hoje?",
      },
    ]);
  };

  if (!user) {
    return <Auth onAuth={handleAuth} />;
  }

  return (
    <main className="app-shell" style={{ flexDirection: "row" }}>
      <Sidebar
        sessions={sessions}
        activeSessionId={activeSessionId}
        onSelect={selectSession}
        onNew={createSessionAndSelect}
        onDelete={deleteSessionAndRefresh}
      />
      <div style={{ flex: 1, display: "flex", flexDirection: "column", minWidth: 0 }}>
        <header className="app-header" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div className="brand">ChatLLM Lab</div>
          <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
            <span style={{ fontSize: "0.85rem", color: "var(--muted)" }}>{user.email}</span>
            <button
              onClick={handleLogout}
              style={{
                background: "none",
                border: "1px solid var(--border)",
                borderRadius: "8px",
                padding: "4px 12px",
                fontSize: "0.8rem",
                color: "var(--muted)",
                cursor: "pointer",
              }}
            >
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

        <div className="warning-banner">Lembre-se, voce precisa focar no experimento!!!</div>
      </div>
    </main>
  );
}

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(<App />);
              color: "var(--muted)",
              cursor: "pointer",
            }}
          >
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

      <div className="warning-banner">Lembre-se, voce precisa focar no experimento!!!</div>
    </main>
  );
}

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(<App />);

