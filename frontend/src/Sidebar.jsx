const { useState } = React;

function Sidebar({ sessions, activeSessionId, onSelectSession, onCreateSession, onDeleteSession }) {
  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <button type="button" className="sidebar-new-btn" onClick={onCreateSession}>
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true">
            <line x1="8" y1="2" x2="8" y2="14" />
            <line x1="2" y1="8" x2="14" y2="8" />
          </svg>
          Nova conversa
        </button>
      </div>
      <nav className="sidebar-list">
        {sessions.map((session) => (
          <div
            key={session.id}
            className={`sidebar-item ${session.id === activeSessionId ? "active" : ""}`}
            onClick={() => onSelectSession(session.id)}
          >
            <span className="sidebar-item-title">
              {session.title || "Nova conversa"}
            </span>
            <button
              type="button"
              className="sidebar-item-delete"
              onClick={(e) => {
                e.stopPropagation();
                onDeleteSession(session.id);
              }}
              title="Excluir conversa"
            >
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" aria-hidden="true">
                <line x1="3" y1="3" x2="11" y2="11" />
                <line x1="11" y1="3" x2="3" y2="11" />
              </svg>
            </button>
          </div>
        ))}
      </nav>
    </aside>
  );
}