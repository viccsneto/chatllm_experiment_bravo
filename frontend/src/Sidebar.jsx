const { useEffect, useState } = React;

function Sidebar({ sessions, currentSessionId, onSelect, onCreate, onDelete, loading }) {
  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <span className="sidebar-title">Sessoes</span>
        <button className="sidebar-new-btn" onClick={onCreate} title="Nova sessao" disabled={loading}>
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round">
            <line x1="7" y1="1" x2="7" y2="13" />
            <line x1="1" y1="7" x2="13" y2="7" />
          </svg>
        </button>
      </div>

      <nav className="sidebar-list">
        {sessions.length === 0 && (
          <div className="sidebar-empty">Nenhuma sessao</div>
        )}
        {sessions.map((s) => (
          <div
            key={s.id}
            className={`sidebar-item ${s.id === currentSessionId ? "active" : ""}`}
            onClick={() => onSelect(s.id)}
          >
            <span className="sidebar-item-title">
              {s.title || "Nova conversa"}
            </span>
            <button
              className="sidebar-del-btn"
              onClick={(e) => { e.stopPropagation(); onDelete(s.id); }}
              title="Deletar sessao"
            >
              <svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round">
                <line x1="2" y1="2" x2="10" y2="10" />
                <line x1="10" y1="2" x2="2" y2="10" />
              </svg>
            </button>
          </div>
        ))}
      </nav>
    </aside>
  );
}