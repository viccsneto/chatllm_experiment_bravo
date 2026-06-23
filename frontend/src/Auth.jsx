const { useState } = React;

const AUTH_STYLES = `
.auth-container {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-page);
}

.auth-card {
  width: 100%;
  max-width: 380px;
  padding: 40px 32px;
  border: 1px solid var(--border);
  border-radius: 16px;
  background: #fff;
  box-shadow: 0 4px 24px rgba(0,0,0,0.06);
}

.auth-card h1 {
  font-size: 1.5rem;
  font-weight: 600;
  margin: 0 0 4px;
  color: var(--text);
}

.auth-card p {
  margin: 0 0 24px;
  color: var(--muted);
  font-size: 0.9rem;
}

.auth-field {
  margin-bottom: 16px;
}

.auth-field label {
  display: block;
  font-size: 0.85rem;
  font-weight: 500;
  margin-bottom: 4px;
  color: var(--text);
}

.auth-field input {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid var(--composer-border);
  border-radius: 10px;
  font: inherit;
  font-size: 0.95rem;
  color: var(--text);
  background: var(--bg-page);
  outline: none;
  box-sizing: border-box;
  transition: border-color 150ms ease;
}

.auth-field input:focus {
  border-color: #b0b0b0;
}

.auth-error {
  color: #c0392b;
  font-size: 0.85rem;
  margin-bottom: 12px;
  text-align: center;
}

.auth-btn {
  width: 100%;
  padding: 11px 16px;
  border: 0;
  border-radius: 10px;
  background: var(--accent);
  color: #fff;
  font: inherit;
  font-size: 0.95rem;
  font-weight: 500;
  cursor: pointer;
  transition: background 120ms ease;
}

.auth-btn:hover {
  background: var(--accent-hover);
}

.auth-btn:disabled {
  background: #d9d9d9;
  cursor: not-allowed;
}

.auth-switch {
  text-align: center;
  margin-top: 16px;
  font-size: 0.85rem;
  color: var(--muted);
}

.auth-switch button {
  background: none;
  border: none;
  color: var(--accent);
  font: inherit;
  font-size: 0.85rem;
  font-weight: 500;
  cursor: pointer;
  text-decoration: underline;
}

.auth-switch button:hover {
  color: var(--accent-hover);
}
`;

function Auth({ onAuth }) {
  const [mode, setMode] = useState("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const isRegister = mode === "register";

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
      setError("A senha deve ter no minimo 6 caracteres.");
      return;
    }

    setLoading(true);
    try {
      const endpoint = isRegister ? "/api/auth/register" : "/api/auth/login";
      const res = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: email.trim(), password }),
      });

      const data = await res.json();

      if (!res.ok) {
        setError(data.detail || "Erro ao autenticar.");
        setLoading(false);
        return;
      }

      localStorage.setItem("access_token", data.access_token);
      localStorage.setItem("user_email", data.email);
      onAuth({ token: data.access_token, email: data.email });
    } catch (err) {
      setError("Erro de conexao com o servidor.");
    } finally {
      setLoading(false);
    }
  };

  const switchMode = () => {
    setMode(isRegister ? "login" : "register");
    setError("");
    setConfirmPassword("");
  };

  return (
    <div className="auth-container">
      <style>{AUTH_STYLES}</style>
      <form className="auth-card" onSubmit={handleSubmit}>
        <h1>{isRegister ? "Criar Conta" : "Entrar"}</h1>
        <p>{isRegister ? "Cadastre-se para usar o ChatLLM Lab" : "Entre com sua conta do ChatLLM Lab"}</p>

        {error && <div className="auth-error">{error}</div>}

        <div className="auth-field">
          <label htmlFor="auth-email">Email</label>
          <input
            id="auth-email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="seu@email.com"
            autoFocus
            disabled={loading}
          />
        </div>

        <div className="auth-field">
          <label htmlFor="auth-password">Senha</label>
          <input
            id="auth-password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Minimo 6 caracteres"
            disabled={loading}
          />
        </div>

        {isRegister && (
          <div className="auth-field">
            <label htmlFor="auth-confirm">Confirmar Senha</label>
            <input
              id="auth-confirm"
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              placeholder="Repita a senha"
              disabled={loading}
            />
          </div>
        )}

        <button className="auth-btn" type="submit" disabled={loading}>
          {loading ? "Aguarde..." : isRegister ? "Cadastrar" : "Entrar"}
        </button>

        <div className="auth-switch">
          {isRegister ? "Ja tem conta?" : "Nao tem conta?"}{" "}
          <button type="button" onClick={switchMode} disabled={loading}>
            {isRegister ? "Fazer login" : "Cadastre-se"}
          </button>
        </div>
      </form>
    </div>
  );
}