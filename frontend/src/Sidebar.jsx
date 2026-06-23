const { useEffect, useRef, useState } = React;

function Sidebar({ sessions, activeSessionId, onSelectSession, onNewChat, onDeleteSession }) {
  const [collapsed, setCollapsed] = useState(false);
  const sidebarRef = useRef(null);

  // Fechar sidebar ao clicar fora em mobile
  useEffect(() => {
    const handleClick = (e) => {
      if (sidebarRef.current && !sidebarRef.current.contains(e.target)) {
        // Não recolhe automaticamente em desktop
      }
    };
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  const formatDate = (isoString) => {
    const d = new Date(isoString);
    const now = new Date();
    const diffMs = now - d;
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

    if (diffDays === 0) return "Hoje";
    if (diffDays === 1) return "Ontem";
    if (diffDays < 7) return `Ha ${diffDays} dias`;
    return d.toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit" });
  };

  const grouped = sessions.reduce((acc, s) => {
    const label = formatDate(s.updated_at);
    if (!acc[label]) acc[label] = [];
    acc[label].push(s);
    return acc;
  }, {});

  const orderedKeys = ["Hoje", "Ontem"];
  const otherKeys = Object.keys(grouped).filter((k) => !orderedKeys.includes(k));

  return (
    <aside ref={sidebarRef} className={`sidebar ${collapsed ? "collapsed" : ""}`}>
      <div className="sidebar-header">
        <button className="sidebar-new-btn" onClick={onNewChat} title="Novo chat">
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
            <line x1="8" y1="2" x2="8" y2="14" />
            <line x1="2" y1="8" x2="14" y2="8" />
          </svg>
          {!collapsed && <span>Novo chat</span>}
        </button>
        <button className="sidebar-toggle" onClick={() => setCollapsed(!collapsed)} title={collapsed ? "Expandir" : "Recolher"}>
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
            {collapsed
              ? <polyline points="6,4 10,8 6,12" />
              : <polyline points="10,4 6,8 10,12" />}
          </svg>
        </button>
      </div>

      {!collapsed && (
        <div className="sidebar-list">
          {orderedKeys.concat(otherKeys).map((group) => (
            <div key={group} className="sidebar-group">
              <div className="sidebar-group-label">{group}</div>
              {grouped[group].map((s) => (
                <div
                  key={s.id}
                  className={`sidebar-item ${s.id === activeSessionId ? "active" : ""}`}
                  onClick={() => onSelectSession(s.id)}
                >
                  <svg className="sidebar-item-icon" width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M2,2 L14,2 L14,10 L10,10 L8,13 L6,10 L2,10 Z" />
                  </svg>
                  <span className="sidebar-item-title">{s.title}</span>
                  <button
                    className="sidebar-item-del"
                    onClick={(e) => { e.stopPropagation(); onDeleteSession(s.id); }}
                    title="Excluir"
                  >
                    <svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
                      <line x1="3" y1="3" x2="9" y2="9" />
                      <line x1="9" y1="3" x2="3" y2="9" />
                    </svg>
                  </button>
                </div>
              ))}
            </div>
          ))}
        </div>
      )}
    </aside>
  );
}