const { useState } = React;

function Auth({ onAuth }) {
  const [mode, setMode] = useState("login"); // "login" | "signup"
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError("");
    setLoading(true);

    try {
      const data = await apiAuth(mode, { email, password });
      setToken(data.access_token);
      onAuth(data.email);
    } catch (err) {
      setError(err.message || "Erro inesperado.");
    } finally {
      setLoading(false);
    }
  };

  const toggleMode = () => {
    setMode((prev) => (prev === "login" ? "signup" : "login"));
    setError("");
  };

  return (
    <div className="auth-container">
      <div className="auth-card">
        <h1 className="auth-title">ChatLLM Lab</h1>
        <h2 className="auth-subtitle">
          {mode === "login" ? "Entrar" : "Criar conta"}
        </h2>

        {error && <div className="auth-error">{error}</div>}

        <form onSubmit={handleSubmit} className="auth-form">
          <input
            type="email"
            placeholder="Email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            autoFocus
            className="auth-input"
          />
          <input
            type="password"
            placeholder="Senha"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            minLength={6}
            className="auth-input"
          />
          <button type="submit" disabled={loading} className="auth-button">
            {loading
              ? "Aguarde..."
              : mode === "login"
              ? "Entrar"
              : "Criar conta"}
          </button>
        </form>

        <p className="auth-toggle">
          {mode === "login" ? (
            <>
              Nao tem conta?{" "}
              <button type="button" className="auth-link" onClick={toggleMode}>
                Cadastre-se
              </button>
            </>
          ) : (
            <>
              Ja tem conta?{" "}
              <button type="button" className="auth-link" onClick={toggleMode}>
                Fazer login
              </button>
            </>
          )}
        </p>
      </div>
    </div>
  );
}