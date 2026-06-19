const { useState } = React;

function Auth({ onAuthSuccess }) {
  const [isRegister, setIsRegister] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError("");

    if (!email.trim() || !password.trim()) {
      setError("Preencha todos os campos.");
      return;
    }

    if (isRegister && password !== confirmPassword) {
      setError("As senhas nao conferem.");
      return;
    }

    if (password.length < 6) {
      setError("A senha deve ter pelo menos 6 caracteres.");
      return;
    }

    setLoading(true);
    try {
      const fn = isRegister ? apiRegister : apiLogin;
      const data = await fn(email.trim(), password);
      localStorage.setItem("access_token", data.access_token);
      localStorage.setItem("user_email", data.user.email);
      onAuthSuccess(data.user);
    } catch (err) {
      setError(err.message || "Erro inesperado.");
    } finally {
      setLoading(false);
    }
  };

  const toggleMode = () => {
    setIsRegister(!isRegister);
    setError("");
    setConfirmPassword("");
  };

  return (
    <div className="auth-container">
      <div className="auth-card">
        <h1 className="auth-title">ChatLLM Lab</h1>
        <p className="auth-subtitle">
          {isRegister ? "Crie sua conta" : "Entre com sua conta"}
        </p>

        {error && <div className="auth-error">{error}</div>}

        <form onSubmit={handleSubmit} className="auth-form">
          <input
            type="email"
            placeholder="Email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            disabled={loading}
            autoFocus
            required
          />

          <input
            type="password"
            placeholder="Senha"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            disabled={loading}
            required
          />

          {isRegister && (
            <input
              type="password"
              placeholder="Confirmar senha"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              disabled={loading}
              required
            />
          )}

          <button type="submit" disabled={loading} className="auth-btn">
            {loading
              ? "Aguarde..."
              : isRegister
              ? "Cadastrar"
              : "Entrar"}
          </button>
        </form>

        <p className="auth-toggle">
          {isRegister ? "Ja tem conta?" : "Nao tem conta?"}{" "}
          <button onClick={toggleMode} className="auth-link-btn">
            {isRegister ? "Faca login" : "Cadastre-se"}
          </button>
        </p>
      </div>
    </div>
  );
}