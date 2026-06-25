const { useState } = React;

/* ── Tela de autenticacao (Login / Registro) ────────────── */

function AuthScreen({ onAuthSuccess }) {
  const [mode, setMode] = useState("login"); // "login" | "register"
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const switchMode = () => {
    setMode((m) => (m === "login" ? "register" : "login"));
    setError("");
    setConfirmPassword("");
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");

    const cleanedEmail = email.trim();
    const cleanedPass = password;

    if (!cleanedEmail || !cleanedPass) {
      setError("Preencha todos os campos.");
      return;
    }

    if (mode === "register") {
      if (cleanedPass.length < 6) {
        setError("A senha deve ter pelo menos 6 caracteres.");
        return;
      }
      if (cleanedPass !== confirmPassword) {
        setError("As senhas nao conferem.");
        return;
      }
    }

    setLoading(true);

    try {
      if (mode === "login") {
        await login(cleanedEmail, cleanedPass);
      } else {
        await register(cleanedEmail, cleanedPass);
      }
      // No throw -> success
      const me = await fetchMe();
      if (me) onAuthSuccess(me);
      else setError("Erro ao recuperar dados do usuario.");
    } catch (err) {
      setError(err.message || "Erro inesperado.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="app-shell">
      <header className="app-header">
        <div className="brand">ChatLLM Lab</div>
      </header>

      <section className="auth-screen">
        <div className="auth-card">
          <h2>{mode === "login" ? "Entrar" : "Criar Conta"}</h2>

          {error && <div className="note error">{error}</div>}

          <form onSubmit={handleSubmit} className="auth-form">
            <label>
              Email
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="seu@email.com"
                autoFocus
                disabled={loading}
                autoComplete="email"
              />
            </label>

            <label>
              Senha
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Sua senha"
                disabled={loading}
                autoComplete={mode === "login" ? "current-password" : "new-password"}
              />
            </label>

            {mode === "register" && (
              <label>
                Confirmar Senha
                <input
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="Repita a senha"
                  disabled={loading}
                  autoComplete="new-password"
                />
              </label>
            )}

            <button type="submit" disabled={loading}>
              {loading ? "Aguarde..." : mode === "login" ? "Entrar" : "Cadastrar"}
            </button>
          </form>

          <p className="auth-switch">
            {mode === "login" ? (
              <>
                Nao tem conta?{" "}
                <a href="#" onClick={(e) => { e.preventDefault(); switchMode(); }}>
                  Cadastre-se
                </a>
              </>
            ) : (
              <>
                Ja tem conta?{" "}
                <a href="#" onClick={(e) => { e.preventDefault(); switchMode(); }}>
                  Faca login
                </a>
              </>
            )}
          </p>
        </div>
      </section>

      <div className="warning-banner">Lembre-se, voce precisa focar no experimento!!!</div>
    </main>
  );
}