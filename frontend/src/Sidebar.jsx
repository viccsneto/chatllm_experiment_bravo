function Sidebar({ sessions, currentSessionId, onSelectSession, onNewSession, onDeleteSession }) {
  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <button className="new-chat-btn" onClick={onNewSession}>
          <span className="new-chat-icon">+</span> Nova conversa
        </button>
      </div>
      <div className="sidebar-list">
        {sessions.length === 0 && (
          <p className="sidebar-empty">Nenhuma conversa ainda</p>
        )}
        {sessions.map((s) => (
          <div
            key={s.id}
            className={`sidebar-item ${s.id === currentSessionId ? "active" : ""}`}
            onClick={() => onSelectSession(s.id)}
          >
            <div className="sidebar-item-title">
              {s.title || "Conversa sem t\u00edtulo"}
            </div>
            <button
              className="sidebar-item-delete"
              title="Excluir conversa"
              onClick={(e) => {
                e.stopPropagation();
                onDeleteSession(s.id);
              }}
            >
              &times;
            </button>
          </div>
        ))}
      </div>
    </aside>
  );
}