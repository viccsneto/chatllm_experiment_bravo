const { useState } = React;

function LoginPage({ onAuthSuccess }) {
  const [mode, setMode] = useState("login"); // "login" | "signup"
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (event) => {
    event.preventDefault();
    const cleanedEmail = email.trim();
    if (!cleanedEmail || !password) return;

    setError("");
    setLoading(true);

    try {
      if (mode === "signup") {
        await signup(cleanedEmail, password);
      } else {
        await login(cleanedEmail, password);
      }
      onAuthSuccess();
    } catch (err) {
      setError(err.message || "Ocorreu um erro inesperado.");
    } finally {
      setLoading(false);
    }
  };

  const switchMode = () => {
    setMode((prev) => (prev === "login" ? "signup" : "login"));
    setError("");
    setPassword("");
  };

  return (
    <main className="app-shell">
      <header className="app-header">
        <div className="brand">ChatLLM Lab</div>
      </header>

      <div className="auth-page">
        <div className="auth-card">
          <div className="auth-tabs">
            <button
              type="button"
              className={`auth-tab ${mode === "login" ? "active" : ""}`}
              onClick={() => { setMode("login"); setError(""); }}
            >
              Entrar
            </button>
            <button
              type="button"
              className={`auth-tab ${mode === "signup" ? "active" : ""}`}
              onClick={() => { setMode("signup"); setError(""); }}
            >
              Cadastrar
            </button>
          </div>

          <form className="auth-form" onSubmit={handleSubmit}>
            <label className="auth-label">
              Email
              <input
                type="email"
                className="auth-input"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="seu@email.com"
                required
                disabled={loading}
                autoFocus
              />
            </label>

            <label className="auth-label">
              Senha
              <input
                type="password"
                className="auth-input"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder={mode === "signup" ? "Mínimo de 6 caracteres" : "Sua senha"}
                minLength={mode === "signup" ? 6 : 1}
                maxLength={128}
                required
                disabled={loading}
              />
            </label>

            {error && <div className="auth-error">{error}</div>}

            <button
              type="submit"
              className="auth-submit"
              disabled={loading || !email.trim() || !password}
            >
              {loading
                ? "Aguarde..."
                : mode === "login"
                ? "Entrar"
                : "Criar conta"}
            </button>
          </form>

          <p className="auth-switch">
            {mode === "login" ? (
              <>
                Nao tem conta?{" "}
                <button type="button" className="auth-link" onClick={switchMode}>
                  Cadastre-se
                </button>
              </>
            ) : (
              <>
                Ja tem conta?{" "}
                <button type="button" className="auth-link" onClick={switchMode}>
                  Faca login
                </button>
              </>
            )}
          </p>
        </div>
      </div>

      <div className="warning-banner">Lembre-se, voce precisa focar no experimento!!!</div>
    </main>
  );
}