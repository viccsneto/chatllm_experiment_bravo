const { useState, useEffect } = React;

const SIDEBAR_STYLES = `
.sidebar {
  width: 260px;
  min-width: 260px;
  height: 100%;
  display: flex;
  flex-direction: column;
  background: #fafafa;
  border-right: 1px solid var(--border);
}

.sidebar-header {
  padding: 12px 12px 8px;
  border-bottom: 1px solid var(--border);
}

.sidebar-new-btn {
  width: 100%;
  padding: 8px 12px;
  border: 1px dashed var(--composer-border);
  border-radius: 10px;
  background: transparent;
  font: inherit;
  font-size: 0.85rem;
  color: var(--text);
  cursor: pointer;
  transition: background 120ms ease, border-color 120ms ease;
}

.sidebar-new-btn:hover {
  background: #eee;
  border-color: #b0b0b0;
}

.sidebar-list {
  flex: 1;
  overflow-y: auto;
  padding: 6px;
}

.sidebar-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 10px;
  border-radius: 8px;
  cursor: pointer;
  transition: background 100ms ease;
  margin-bottom: 2px;
}

.sidebar-item:hover {
  background: #eaeaea;
}

.sidebar-item.active {
  background: #e0e0e0;
  font-weight: 500;
}

.sidebar-item-title {
  flex: 1;
  font-size: 0.82rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--text);
}

.sidebar-item-del {
  flex-shrink: 0;
  width: 20px;
  height: 20px;
  border: none;
  background: transparent;
  border-radius: 4px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--muted);
  font-size: 0.75rem;
  opacity: 0;
  transition: opacity 100ms ease;
}

.sidebar-item:hover .sidebar-item-del {
  opacity: 1;
}

.sidebar-item-del:hover {
  background: #d0d0d0;
  color: #c0392b;
}

@media (max-width: 768px) {
  .sidebar {
    width: 200px;
    min-width: 200px;
  }
}
`;

function Sidebar({ sessions, activeSessionId, onSelect, onNew, onDelete }) {
  return (
    <div className="sidebar">
      <style>{SIDEBAR_STYLES}</style>
      <div className="sidebar-header">
        <button className="sidebar-new-btn" onClick={onNew}>
          + Novo Chat
        </button>
      </div>
      <div className="sidebar-list">
        {sessions.map((s) => (
          <div
            key={s.id}
            className={`sidebar-item ${s.id === activeSessionId ? "active" : ""}`}
            onClick={() => onSelect(s.id)}
          >
            <span className="sidebar-item-title">{s.title}</span>
            <button
              className="sidebar-item-del"
              onClick={(e) => { e.stopPropagation(); onDelete(s.id); }}
              title="Excluir sessao"
            >
              ×
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}