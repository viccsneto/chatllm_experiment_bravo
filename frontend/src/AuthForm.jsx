const { useState } = React;

function AuthForm({ mode, busy, error, onChangeMode, onSubmit }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const isRegister = mode === "register";

  const handleSubmit = (event) => {
    event.preventDefault();
    onSubmit({ email: email.trim(), password });
  };

  return (
    <main className="auth-shell">
      <section className="auth-card" aria-labelledby="auth-title">
        <div className="auth-brand">ChatLLM Lab</div>
        <h1 id="auth-title">{isRegister ? "Criar conta" : "Entrar"}</h1>
        <p className="auth-subtitle">
          {isRegister
            ? "Cadastre-se para comecar a conversar."
            : "Entre para acessar suas conversas."}
        </p>

        <form className="auth-form" onSubmit={handleSubmit}>
          <label htmlFor="email">E-mail</label>
          <input
            id="email"
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            autoComplete="email"
            maxLength={254}
            required
            autoFocus
          />

          <label htmlFor="password">Senha</label>
          <input
            id="password"
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            autoComplete={isRegister ? "new-password" : "current-password"}
            minLength={8}
            maxLength={128}
            required
          />
          {isRegister && (
            <span className="field-help">Use pelo menos 8 caracteres.</span>
          )}

          {error && <div className="auth-error" role="alert">{error}</div>}

          <button className="auth-submit" type="submit" disabled={busy}>
            {busy ? "Aguarde..." : isRegister ? "Criar conta" : "Entrar"}
          </button>
        </form>

        <button
          className="auth-switch"
          type="button"
          disabled={busy}
          onClick={() => onChangeMode(isRegister ? "login" : "register")}
        >
          {isRegister ? "Ja tenho uma conta" : "Ainda nao tenho uma conta"}
        </button>
      </section>
      <div className="warning-banner">Lembre-se, você precisa focar no experimento!!!</div>
    </main>
  );
}
