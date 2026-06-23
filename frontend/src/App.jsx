const { useEffect, useMemo, useRef, useState, useCallback } = React;

function createMessageId() {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

// ── Auth Screen ───────────────────────────────────────

function AuthScreen() {
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
        await apiRegister(email, password);
      }
      window.location.reload();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="app-shell">
      <header className="app-header">
        <div className="brand">ChatLLM Lab</div>
      </header>
      <div className="auth-container">
        <form className="auth-form" onSubmit={handleSubmit}>
          <h2>{mode === "login" ? "Entrar" : "Criar Conta"}</h2>
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
          {error && <div className="auth-error">{error}</div>}
          <button type="submit" disabled={loading}>
            {loading ? "Aguarde..." : mode === "login" ? "Entrar" : "Cadastrar"}
          </button>
          <p className="auth-toggle">
            {mode === "login" ? (
              <>
                Nao tem conta?{" "}
                <a href="#" onClick={(e) => { e.preventDefault(); setMode("register"); setError(""); }}>
                  Cadastre-se
                </a>
              </>
            ) : (
              <>
                Ja tem conta?{" "}
                <a href="#" onClick={(e) => { e.preventDefault(); setMode("login"); setError(""); }}>
                  Fazer login
                </a>
              </>
            )}
          </p>
        </form>
      </div>
    </main>
  );
}

// ── Sidebar ──────────────────────────────────────────

function Sidebar({ sessions, currentSessionId, onSelectSession, onNewSession, onDeleteSession, onLogout, user }) {
  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <button className="btn-new-chat" onClick={onNewSession}>
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
            <line x1="8" y1="2" x2="8" y2="14" />
            <line x1="2" y1="8" x2="14" y2="8" />
          </svg>
          Nova conversa
        </button>
      </div>
      <div className="sidebar-list">
        {sessions.map((s) => (
          <div
            key={s.id}
            className={`sidebar-item ${s.id === currentSessionId ? "active" : ""}`}
            onClick={() => onSelectSession(s.id)}
          >
            <span className="sidebar-item-title" title={s.title || "Nova conversa"}>{s.title || "Nova conversa"}</span>
            <button
              className="sidebar-item-delete"
              onClick={(e) => { e.stopPropagation(); onDeleteSession(s.id); }}
              title="Deletar sessao"
            >
              <svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                <line x1="1" y1="1" x2="11" y2="11" />
                <line x1="11" y1="1" x2="1" y2="11" />
              </svg>
            </button>
          </div>
        ))}
      </div>
      <div className="sidebar-footer">
        <span className="sidebar-user">{user.email}</span>
        <button className="btn-logout-sidebar" onClick={onLogout}>Logout</button>
      </div>
    </aside>
  );
}

// ── Chat Screen ──────────────────────────────────────

function ChatScreen({ user, onLogout }) {
  const [sessions, setSessions] = useState([]);
  const [currentSessionId, setCurrentSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const messagesRef = useRef(null);
  const abortControllerRef = useRef(null);

  // Carregar sessoes ao montar
  useEffect(() => {
    apiListSessions().then((list) => {
      setSessions(list);
      if (list.length > 0) {
        setCurrentSessionId(list[0].id);
      } else {
        // Criar primeira sessao automaticamente
        apiCreateSession().then((s) => {
          setSessions([s]);
          setCurrentSessionId(s.id);
        });
      }
    }).catch(() => {});
  }, []);

  // Carregar mensagens da sessao atual
  useEffect(() => {
    if (!currentSessionId) return;
    apiGetSessionMessages(currentSessionId).then((msgs) => {
      setMessages(msgs.length > 0
        ? msgs.map((m) => ({ id: createMessageId(), role: m.role, content: m.content }))
        : [{ id: createMessageId(), role: "assistant", content: "Bem-vindo ao ChatLLM Lab. Como posso ajudar voce hoje?" }]
      );
    }).catch(() => {
      setMessages([{ id: createMessageId(), role: "assistant", content: "Bem-vindo ao ChatLLM Lab. Como posso ajudar voce hoje?" }]);
    });
  }, [currentSessionId]);

  useEffect(() => {
    const el = messagesRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages]);

  useEffect(() => {
    return () => {
      abortControllerRef.current?.abort();
    };
  }, []);

  const chatHistory = useMemo(
    () => messages.filter((msg) => msg.role === "user" || msg.role === "assistant"),
    [messages]
  );

  const onStop = () => {
    abortControllerRef.current?.abort();
    abortControllerRef.current = null;
    setBusy(false);
  };

  const handleNewSession = async () => {
    try {
      const session = await apiCreateSession();
      setSessions((prev) => [session, ...prev]);
      setCurrentSessionId(session.id);
    } catch (err) {
      setError(err.message);
    }
  };

  const handleSelectSession = (sessionId) => {
    if (busy) return;
    setCurrentSessionId(sessionId);
  };

  const handleDeleteSession = async (sessionId) => {
    try {
      await apiDeleteSession(sessionId);
      const updated = sessions.filter((s) => s.id !== sessionId);
      setSessions(updated);
      if (currentSessionId === sessionId) {
        if (updated.length > 0) {
          setCurrentSessionId(updated[0].id);
        } else {
          const session = await apiCreateSession();
          setSessions([session]);
          setCurrentSessionId(session.id);
        }
      }
    } catch (err) {
      setError(err.message);
    }
  };

  const handleTitleUpdate = (title, sessionId) => {
    setSessions((prev) =>
      prev.map((s) => (s.id === sessionId ? { ...s, title } : s))
    );
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
      const sessionId = await sendMessageStream({
        message: cleaned,
        history: chatHistory,
        sessionId: currentSessionId,
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
        onTitle: handleTitleUpdate,
      });

      if (sessionId && sessionId !== currentSessionId) {
        setCurrentSessionId(sessionId);
      }

      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === assistantMessageId && !msg.content.trim()
            ? { ...msg, content: "Nao foi possivel obter resposta do modelo agora." }
            : msg
        )
      );

      // Recarregar sessoes para pegar titulos atualizados
      apiListSessions().then(setSessions).catch(() => {});
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

  return (
    <div className="app-layout">
      {sidebarOpen && (
        <Sidebar
          sessions={sessions}
          currentSessionId={currentSessionId}
          onSelectSession={handleSelectSession}
          onNewSession={handleNewSession}
          onDeleteSession={handleDeleteSession}
          onLogout={onLogout}
          user={user}
        />
      )}

      <main className="app-shell">
        <header className="app-header">
          <button className="btn-toggle-sidebar" onClick={() => setSidebarOpen(!sidebarOpen)}>
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <line x1="3" y1="5" x2="17" y2="5" />
              <line x1="3" y1="10" x2="17" y2="10" />
              <line x1="3" y1="15" x2="17" y2="15" />
            </svg>
          </button>
          <div className="brand">ChatLLM Lab</div>
          <div className="header-right" />
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

// ── App (root) ────────────────────────────────────────

function App() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (getToken()) {
      apiMe().then((u) => {
        setUser(u);
        setLoading(false);
      }).catch(() => {
        clearToken();
        setLoading(false);
      });
    } else {
      setLoading(false);
    }
  }, []);

  const handleLogout = async () => {
    try {
      await apiLogout();
    } catch {
      clearToken();
    }
    window.location.reload();
  };

  if (loading) {
    return (
      <main className="app-shell">
        <header className="app-header">
          <div className="brand">ChatLLM Lab</div>
        </header>
        <div className="auth-container">
          <p>Carregando...</p>
        </div>
      </main>
    );
  }

  if (!user) {
    return <AuthScreen />;
  }

  return <ChatScreen user={user} onLogout={handleLogout} />;
}

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(<App />);

