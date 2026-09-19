import {
  LayoutDashboard,
  Bot,
  FolderGit2,
  CheckSquare,
  Camera,
} from 'lucide-react';

export type NavTab = 'overview' | 'agents' | 'workspaces' | 'evaluations' | 'snapshots';

interface SidebarProps {
  activeTab: NavTab;
  onSelectTab: (tab: NavTab) => void;
  mobileMenuOpen: boolean;
  onCloseMobileMenu: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  activeTab,
  onSelectTab,
  mobileMenuOpen,
  onCloseMobileMenu,
}) => {
  const navItems: { id: NavTab; label: string; icon: React.ReactNode; isUpcoming?: boolean }[] = [
    { id: 'overview', label: 'Overview', icon: <LayoutDashboard size={16} /> },
    { id: 'workspaces', label: 'Workspaces', icon: <FolderGit2 size={16} /> },
    { id: 'agents', label: 'Agents', icon: <Bot size={16} /> },
    { id: 'evaluations', label: 'Evaluations', icon: <CheckSquare size={16} /> },
    { id: 'snapshots', label: 'Snapshots', icon: <Camera size={16} />, isUpcoming: true },
  ];

  const handleItemClick = (tab: NavTab) => {
    onSelectTab(tab);
    onCloseMobileMenu();
  };

  return (
    <aside className={`sidebar ${mobileMenuOpen ? 'mobile-open' : ''}`}>
      <div className="nav-group">
        {navItems.map((item) => {
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              className={`nav-item ${isActive ? 'active' : ''}`}
              onClick={() => handleItemClick(item.id)}
            >
              <div className="nav-item-content">
                {item.icon}
                <span>{item.label}</span>
              </div>
              {item.isUpcoming && <span className="phase-tag">Soon</span>}
            </button>
          );
        })}
      </div>

      <div className="sidebar-footer">
        <div>Codex OS Foundation</div>
        <div>Minimal Engineering Shell</div>
      </div>
    </aside>
  );
};
