function Sidebar({ sessions, activeSessionId, loading, disabled, onNew, onSelect }) {
  return (
    <aside className="sidebar" aria-label="Conversas">
      <button
        className="new-chat-button"
        type="button"
        onClick={onNew}
        disabled={loading || disabled}
      >
        <span aria-hidden="true">＋</span>
        Nova conversa
      </button>

      <nav className="session-list" aria-label="Historico de conversas">
        {loading && sessions.length === 0 && (
          <div className="session-placeholder">Carregando...</div>
        )}
        {!loading && sessions.length === 0 && (
          <div className="session-placeholder">Nenhuma conversa ainda.</div>
        )}
        {sessions.map((session) => (
          <button
            key={session.id}
            className={`session-item ${session.id === activeSessionId ? "active" : ""}`}
            type="button"
            title={session.title || "Nova conversa"}
            disabled={disabled}
            onClick={() => onSelect(session.id)}
          >
            {session.title || "Nova conversa"}
          </button>
        ))}
      </nav>
    </aside>
  );
}
