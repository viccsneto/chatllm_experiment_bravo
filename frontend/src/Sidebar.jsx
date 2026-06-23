const { useState } = React;

function Sidebar({ sessions, activeSessionId, onSelectSession, onCreateSession, loading }) {
  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <button className="new-chat-btn" onClick={onCreateSession} disabled={loading}>
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" aria-hidden="true">
            <line x1="7" y1="1" x2="7" y2="13" />
            <line x1="1" y1="7" x2="13" y2="7" />
          </svg>
          Nova conversa
        </button>
      </div>
      <nav className="sidebar-nav">
        {loading && sessions.length === 0 && (
          <div className="sidebar-loading">Carregando...</div>
        )}
        {!loading && sessions.length === 0 && (
          <div className="sidebar-empty">Nenhuma conversa ainda</div>
        )}
        {sessions.map((s) => (
          <button
            key={s.id}
            className={`sidebar-item ${s.id === activeSessionId ? "active" : ""}`}
            onClick={() => onSelectSession(s.id)}
            title={s.title}
          >
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" aria-hidden="true" style={{ flexShrink: 0 }}>
              <rect x="1.5" y="2.5" width="11" height="9" rx="1.5" />
              <line x1="4.5" y1="6" x2="9.5" y2="6" />
              <line x1="4.5" y1="8.5" x2="8" y2="8.5" />
            </svg>
            <span className="sidebar-item-title">{s.title}</span>
          </button>
        ))}
      </nav>
    </aside>
  );
}