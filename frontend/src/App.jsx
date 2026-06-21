const { useEffect, useMemo, useRef, useState } = React;

function createMessageId() {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

function AuthScreen({ onAuthSuccess }) {
  const [mode, setMode] = useState("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [authError, setAuthError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setAuthError("");
    setLoading(true);
    try {
      if (mode === "login") {
        await login(email, password);
      } else {
        await signup(email, password);
      }
      onAuthSuccess();
    } catch (err) {
      setAuthError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-screen">
      <div className="auth-box">
        <h2>{mode === "login" ? "Entrar" : "Criar Conta"}</h2>
        <p className="subtitle">
          {mode === "login"
            ? "Acesse o ChatLLM Lab com seu email."
            : "Cadastre-se para usar o ChatLLM Lab."}
        </p>
        <form onSubmit={handleSubmit}>
          <div className="auth-field">
            <label htmlFor="auth-email">Email</label>
            <input
              id="auth-email"
              type="email"
              placeholder="seu@email.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoFocus
            />
          </div>
          <div className="auth-field">
            <label htmlFor="auth-password">Senha</label>
            <input
              id="auth-password"
              type="password"
              placeholder="Minimo 6 caracteres"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={6}
            />
          </div>
          <button className="auth-btn" type="submit" disabled={loading}>
            {loading ? "Aguarde..." : mode === "login" ? "Entrar" : "Cadastrar"}
          </button>
          {authError && <p className="auth-error">{authError}</p>}
        </form>
        <div className="auth-switch">
          {mode === "login" ? (
            <>
              Nao tem conta?{" "}
              <button type="button" onClick={() => { setMode("signup"); setAuthError(""); }}>
                Cadastre-se
              </button>
            </>
          ) : (
            <>
              Ja tem conta?{" "}
              <button type="button" onClick={() => { setMode("login"); setAuthError(""); }}>
                Faca login
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

function App() {
  const [user, setUser] = useState(null);
  const [checkingAuth, setCheckingAuth] = useState(true);
  const [sessions, setSessions] = useState([]);
  const [currentSessionId, setCurrentSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
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
    (async () => {
      if (getToken()) {
        try {
          const me = await getMe();
          setUser(me);
          const sess = await listSessions();
          setSessions(sess);
          const lastId = localStorage.getItem("chatllm_session_id");
          if (lastId && sess.some((s) => s.id === Number(lastId))) {
            setCurrentSessionId(Number(lastId));
            const msgs = await getSessionMessages(Number(lastId));
            setMessages(msgs.map((m) => ({ id: `srv-${m.id}`, role: m.role, content: m.content })));
          } else if (sess.length > 0) {
            await selectSessionByData(sess[0].id, sess);
          }
        } catch {
          clearToken();
        }
      }
      setCheckingAuth(false);
    })();
    return () => {
      abortControllerRef.current?.abort();
    };
  }, []);

  const selectSessionByData = async (id, sessList) => {
    setCurrentSessionId(id);
    localStorage.setItem("chatllm_session_id", id);
    const msgs = await getSessionMessages(id);
    if (msgs.length > 0) {
      setMessages(msgs.map((m) => ({ id: `srv-${m.id}`, role: m.role, content: m.content })));
    } else {
      setMessages([{
        id: createMessageId(),
        role: "assistant",
        content: "Bem-vindo ao ChatLLM Lab. Como posso ajudar voce hoje?",
      }]);
    }
  };

  const handleNewSession = async () => {
    const sess = await createSession();
    setSessions((prev) => [sess, ...prev]);
    await selectSessionByData(sess.id, [sess, ...sessions]);
  };

  const handleDeleteSession = async (id) => {
    await deleteSession(id);
    const updated = sessions.filter((s) => s.id !== id);
    setSessions(updated);
    if (currentSessionId === id) {
      if (updated.length > 0) {
        await selectSessionByData(updated[0].id, updated);
      } else {
        setCurrentSessionId(null);
        setMessages([]);
        localStorage.removeItem("chatllm_session_id");
      }
    }
  };

  const handleLogout = async () => {
    await logout();
    setUser(null);
    setSessions([]);
    setCurrentSessionId(null);
    setMessages([]);
    localStorage.removeItem("chatllm_session_id");
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
        session_id: currentSessionId,
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
        onDone: (sessionId) => {
          // Se a sessao foi criada automaticamente, adota-la
          if (sessionId && !currentSessionId) {
            setCurrentSessionId(sessionId);
            localStorage.setItem("chatllm_session_id", sessionId);
          }
          // refresh sidebar titles after response
          listSessions().then(setSessions);
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

  if (checkingAuth) {
    return (
      <main className="app-shell">
        <div className="auth-screen">
          <p>Verificando sessao...</p>
        </div>
      </main>
    );
  }

  if (!user) {
    return (
      <main className="app-shell">
        <AuthScreen onAuthSuccess={async () => {
          try {
            const me = await getMe();
            setUser(me);
            const sess = await listSessions();
            setSessions(sess);
            if (sess.length > 0) {
              await selectSessionByData(sess[0].id, sess);
            }
          } catch {
            clearToken();
          }
        }} />
      </main>
    );
  }

  return (
    <main className="app-shell">
      <Sidebar
        sessions={sessions}
        currentSessionId={currentSessionId}
        onSelectSession={(id) => {
          if (busy) return; // bloqueia troca durante streaming
          const list = sessions;
          setCurrentSessionId(id);
          localStorage.setItem("chatllm_session_id", id);
          getSessionMessages(id).then((msgs) => {
            if (msgs.length > 0) {
              setMessages(msgs.map((m) => ({ id: `srv-${m.id}`, role: m.role, content: m.content })));
            } else {
              setMessages([{
                id: createMessageId(),
                role: "assistant",
                content: "Bem-vindo ao ChatLLM Lab. Como posso ajudar voce hoje?",
              }]);
            }
          });
        }}
        onNewSession={handleNewSession}
        onDeleteSession={handleDeleteSession}
      />
      <div className="chat-area">
        <header className="app-header">
          <div className="app-header-inner">
            <div className="brand">ChatLLM Lab</div>
            <button className="logout-btn" onClick={handleLogout}>
              Sair ({user.email})
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

