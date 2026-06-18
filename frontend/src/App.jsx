const { useEffect, useMemo, useRef, useState } = React;

function createMessageId() {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

function AuthForm({ onAuthSuccess }) {
  const [mode, setMode] = useState("login"); // "login" | "signup"
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [authError, setAuthError] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();
    setAuthError("");
    setLoading(true);
    try {
      const fn = mode === "login" ? login : signup;
      const result = await fn(email, password);
      onAuthSuccess(result.user);
    } catch (err) {
      setAuthError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const toggleMode = () => {
    setMode((m) => (m === "login" ? "signup" : "login"));
    setAuthError("");
  };

  return (
    <div style={{
      display: "flex", alignItems: "center", justifyContent: "center",
      height: "100%", width: "100%",
    }}>
      <form onSubmit={handleSubmit} style={{
        display: "flex", flexDirection: "column", gap: "16px",
        width: "100%", maxWidth: "360px", padding: "32px",
      }}>
        <h1 style={{ fontSize: "1.5rem", fontWeight: 600, margin: 0, textAlign: "center" }}>
          ChatLLM Lab
        </h1>
        <p style={{ margin: 0, textAlign: "center", color: "var(--muted)", fontSize: "0.9rem" }}>
          {mode === "login" ? "Entre com sua conta" : "Crie sua conta"}
        </p>

        {authError && (
          <div style={{
            color: "#e53e3e", background: "#fff5f5", padding: "10px 14px",
            borderRadius: "8px", fontSize: "0.85rem", border: "1px solid #fed7d7",
          }}>{authError}</div>
        )}

        <input
          type="email"
          placeholder="Seu email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          style={{
            padding: "10px 14px", borderRadius: "8px", border: "1px solid var(--composer-border)",
            font: "inherit", fontSize: "1rem", outline: "none",
          }}
        />
        <input
          type="password"
          placeholder="Sua senha"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          minLength={mode === "signup" ? 6 : 1}
          style={{
            padding: "10px 14px", borderRadius: "8px", border: "1px solid var(--composer-border)",
            font: "inherit", fontSize: "1rem", outline: "none",
          }}
        />
        <button
          type="submit"
          disabled={loading}
          style={{
            padding: "10px", borderRadius: "8px", border: "none",
            background: "var(--accent)", color: "#fff", fontWeight: 600,
            fontSize: "1rem", cursor: loading ? "not-allowed" : "pointer",
            opacity: loading ? 0.7 : 1,
          }}
        >
          {loading ? "Aguarde..." : mode === "login" ? "Entrar" : "Criar conta"}
        </button>

        <button
          type="button"
          onClick={toggleMode}
          style={{
            background: "none", border: "none", color: "var(--muted)",
            cursor: "pointer", fontSize: "0.85rem", textDecoration: "underline",
          }}
        >
          {mode === "login"
            ? "Nao tem conta? Cadastre-se"
            : "Ja tem conta? Faca login"}
        </button>
      </form>
    </div>
  );
}

function App() {
  const [user, setUser] = useState(null);
  const [loadingAuth, setLoadingAuth] = useState(true);
  const [messages, setMessages] = useState([]);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const messagesRef = useRef(null);
  const abortControllerRef = useRef(null);

  // Verificar sessao ao montar
  useEffect(() => {
    fetchMe()
      .then((u) => {
        setUser(u);
        setMessages([{
          id: createMessageId(),
          role: "assistant",
          content: `Bem-vindo(a) ao ChatLLM Lab, ${u.email}! Como posso ajudar voce hoje?`,
        }]);
      })
      .catch(() => {
        setUser(null);
        setMessages([]);
      })
      .finally(() => setLoadingAuth(false));
  }, []);

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

  const onSubmit = async (event) => {
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

  const handleLogout = async () => {
    try {
      await logout();
    } catch { /* ignore */ }
    setUser(null);
    setMessages([]);
  };

  // Tela de carregamento inicial
  if (loadingAuth) {
    return (
      <main className="app-shell">
        <div style={{
          display: "flex", alignItems: "center", justifyContent: "center",
          height: "100%", fontSize: "1rem", color: "var(--muted)",
        }}>
          Carregando...
        </div>
      </main>
    );
  }

  // Tela de login/cadastro
  if (!user) {
    return (
      <main className="app-shell">
        <AuthForm onAuthSuccess={(u) => {
          setUser(u);
          setMessages([{
            id: createMessageId(),
            role: "assistant",
            content: `Bem-vindo(a) ao ChatLLM Lab, ${u.email}! Como posso ajudar voce hoje?`,
          }]);
        }} />
      </main>
    );
  }

  // Chat autenticado
  return (
    <main className="app-shell">
      <header className="app-header" style={{
        display: "flex", justifyContent: "space-between", alignItems: "center",
      }}>
        <div className="brand">ChatLLM Lab</div>
        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <span style={{ fontSize: "0.85rem", color: "var(--muted)" }}>{user.email}</span>
          <button
            onClick={handleLogout}
            style={{
              background: "none", border: "1px solid var(--border)", borderRadius: "6px",
              padding: "4px 12px", cursor: "pointer", fontSize: "0.85rem",
              color: "var(--text)",
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

