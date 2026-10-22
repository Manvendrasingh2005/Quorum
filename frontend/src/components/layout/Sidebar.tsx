import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Plus,
  Clock,
  FileText,
  BarChart3,
  BookOpen,
  MoreVertical,
  ChevronDown,
  Settings,
  LogOut,
  Key,
  PanelLeftClose,
  PanelLeft,
  X,
  Compass,
} from 'lucide-react';
import { QuorumLogo } from '../logo/QuorumLogo';
import { useAuth } from '../../hooks/useAuth';

export type NavItem = 'workspace' | 'history' | 'reports' | 'usage' | 'docs';

interface SidebarProps {
  currentTab: NavItem;
  onSelectTab: (tab: NavItem) => void;
  onNewResearch: () => void;
  isMobileOpen: boolean;
  onCloseMobile: () => void;
  onSignOut: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  currentTab,
  onSelectTab,
  onNewResearch,
  isMobileOpen,
  onCloseMobile,
  onSignOut,
}) => {
  const { user, isLoading } = useAuth();
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [showUserMenu, setShowUserMenu] = useState(false);
  const [showWorkspaceMenu, setShowWorkspaceMenu] = useState(false);
  const [activeWorkspace, setActiveWorkspace] = useState('Personal Workspace');

  const navItems = [
    { id: 'workspace' as NavItem, label: 'Workspace', icon: Compass, badge: null },
    { id: 'history' as NavItem, label: 'Research History', icon: Clock, badge: '12' },
    { id: 'reports' as NavItem, label: 'Verified Reports', icon: FileText, badge: '5' },
    { id: 'usage' as NavItem, label: 'Usage & Quota', icon: BarChart3, badge: null },
    { id: 'docs' as NavItem, label: 'Documentation', icon: BookOpen, badge: null },
  ];

  const sidebarContent = (
    <div className="flex flex-col h-full justify-between p-4 bg-[#0c0d0f] border-r border-white/[0.08] text-zinc-300 select-none">
      {/* Top Header Section */}
      <div className="space-y-4">
        {/* Logo & Workspace row */}
        <div className="flex items-center justify-between pb-2 border-b border-white/[0.06]">
          <div className="flex items-center gap-2.5 overflow-hidden">
            <QuorumLogo size={24} className="text-white shrink-0" />
            {!isCollapsed && (
              <span className="font-semibold text-base tracking-tight text-white font-sans truncate">
                quorum.
              </span>
            )}
          </div>

          <div className="flex items-center gap-1">
            {/* Desktop Collapse Toggle */}
            <button
              onClick={() => setIsCollapsed(!isCollapsed)}
              className="hidden lg:flex p-1.5 rounded-lg text-zinc-400 hover:text-white hover:bg-white/[0.06] transition-colors cursor-pointer"
              title={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            >
              {isCollapsed ? <PanelLeft className="w-4 h-4" /> : <PanelLeftClose className="w-4 h-4" />}
            </button>

            {/* Mobile Close Button */}
            <button
              onClick={onCloseMobile}
              className="lg:hidden p-1.5 rounded-lg text-zinc-400 hover:text-white hover:bg-white/[0.06] transition-colors cursor-pointer"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Workspace Switcher */}
        {!isCollapsed && (
          <div className="relative">
            <button
              onClick={() => setShowWorkspaceMenu(!showWorkspaceMenu)}
              className="w-full flex items-center justify-between px-2.5 py-2 rounded-xl bg-white/[0.03] hover:bg-white/[0.06] border border-white/[0.06] transition-colors text-xs font-medium text-zinc-200 cursor-pointer"
            >
              <div className="flex items-center gap-2 truncate">
                <div className="w-4 h-4 rounded bg-gradient-to-tr from-indigo-500 to-purple-500 flex items-center justify-center text-[9px] font-bold text-white shrink-0">
                  Q
                </div>
                <span className="truncate">{activeWorkspace}</span>
              </div>
              <ChevronDown className="w-3.5 h-3.5 text-zinc-400 shrink-0" />
            </button>

            <AnimatePresence>
              {showWorkspaceMenu && (
                <motion.div
                  initial={{ opacity: 0, y: -4 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -4 }}
                  className="absolute left-0 right-0 top-full mt-1.5 z-50 p-1.5 rounded-xl bg-[#141518] border border-white/10 shadow-2xl space-y-1 text-xs"
                >
                  <button
                    onClick={() => {
                      setActiveWorkspace('Personal Workspace');
                      setShowWorkspaceMenu(false);
                    }}
                    className={`w-full text-left px-2.5 py-1.5 rounded-lg transition-colors cursor-pointer ${
                      activeWorkspace === 'Personal Workspace'
                        ? 'bg-white/10 text-white font-medium'
                        : 'text-zinc-400 hover:text-white hover:bg-white/5'
                    }`}
                  >
                    Personal Workspace (Pro)
                  </button>
                  <button
                    onClick={() => {
                      setActiveWorkspace('Autonomous Labs');
                      setShowWorkspaceMenu(false);
                    }}
                    className={`w-full text-left px-2.5 py-1.5 rounded-lg transition-colors cursor-pointer ${
                      activeWorkspace === 'Autonomous Labs'
                        ? 'bg-white/10 text-white font-medium'
                        : 'text-zinc-400 hover:text-white hover:bg-white/5'
                    }`}
                  >
                    Autonomous Labs (Team)
                  </button>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        )}

        {/* New Research Button */}
        <button
          onClick={onNewResearch}
          className={`w-full group flex items-center justify-center gap-2 py-2.5 rounded-xl bg-white text-zinc-950 hover:bg-zinc-100 active:scale-[0.98] transition-all font-medium text-xs cursor-pointer shadow-sm shadow-white/5 ${
            isCollapsed ? 'px-2' : 'px-3'
          }`}
          title="New research session (⌘N)"
        >
          <Plus className="w-4 h-4 shrink-0" />
          {!isCollapsed && <span>New research</span>}
        </button>

        {/* Navigation Items */}
        <nav className="space-y-1 pt-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = currentTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => {
                  onSelectTab(item.id);
                  onCloseMobile();
                }}
                className={`w-full flex items-center gap-3 px-3 py-2 rounded-xl text-xs font-medium transition-all cursor-pointer ${
                  isActive
                    ? 'bg-white/[0.08] text-white shadow-sm'
                    : 'text-zinc-400 hover:text-zinc-200 hover:bg-white/[0.04]'
                } ${isCollapsed ? 'justify-center px-2' : 'justify-between'}`}
                title={item.label}
              >
                <div className="flex items-center gap-2.5 truncate">
                  <Icon className={`w-4 h-4 shrink-0 ${isActive ? 'text-white' : 'text-zinc-400'}`} />
                  {!isCollapsed && <span className="truncate">{item.label}</span>}
                </div>

                {!isCollapsed && item.badge && (
                  <span className="px-1.5 py-0.5 rounded-full text-[10px] font-mono bg-white/[0.06] text-zinc-400 border border-white/[0.06]">
                    {item.badge}
                  </span>
                )}
              </button>
            );
          })}
        </nav>
      </div>

      {/* Bottom User Profile Row with Popover Menu */}
      <div className="relative pt-4 border-t border-white/[0.06]">
        <div
          onClick={() => setShowUserMenu(!showUserMenu)}
          className={`flex items-center rounded-xl p-2 bg-white/[0.02] hover:bg-white/[0.06] transition-colors cursor-pointer ${
            isCollapsed ? 'justify-center' : 'justify-between'
          }`}
        >
          <div className="flex items-center gap-2.5 overflow-hidden">
            <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-emerald-500 to-teal-400 flex items-center justify-center text-xs font-bold text-zinc-950 shrink-0">
              {user?.name ? user.name[0].toUpperCase() : (user?.email ? user.email[0].toUpperCase() : 'U')}
            </div>
            {!isCollapsed && (
              <div className="text-left truncate">
                <p className="text-xs font-medium text-white truncate">
                  {user?.name || (isLoading ? 'Authenticating...' : (user?.email ? user.email.split('@')[0] : 'Researcher'))}
                </p>
                <p className="text-[11px] text-zinc-500 truncate">
                  {user?.email || (isLoading ? 'Syncing profile...' : '')}
                </p>
              </div>
            )}
          </div>

          {!isCollapsed && (
            <MoreVertical className="w-4 h-4 text-zinc-400 shrink-0 hover:text-white" />
          )}
        </div>

        {/* User Popover Menu */}
        <AnimatePresence>
          {showUserMenu && (
            <motion.div
              initial={{ opacity: 0, y: 8, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 8, scale: 0.95 }}
              className={`absolute bottom-full mb-2 z-50 p-1.5 rounded-xl bg-[#141518] border border-white/10 shadow-2xl space-y-1 text-xs ${
                isCollapsed ? 'left-full ml-2 w-48' : 'left-0 right-0'
              }`}
            >
              <button
                onClick={() => {
                  setShowUserMenu(false);
                }}
                className="w-full flex items-center gap-2 px-2.5 py-1.5 rounded-lg text-zinc-300 hover:text-white hover:bg-white/5 transition-colors cursor-pointer"
              >
                <Settings className="w-3.5 h-3.5 text-zinc-400" />
                <span>Account settings</span>
              </button>
              <button
                onClick={() => {
                  setShowUserMenu(false);
                }}
                className="w-full flex items-center gap-2 px-2.5 py-1.5 rounded-lg text-zinc-300 hover:text-white hover:bg-white/5 transition-colors cursor-pointer"
              >
                <Key className="w-3.5 h-3.5 text-zinc-400" />
                <span>API Keys (Tavily/Gemini)</span>
              </button>
              <div className="h-px bg-white/[0.06] my-1" />
              <button
                onClick={() => {
                  setShowUserMenu(false);
                  onSignOut();
                }}
                className="w-full flex items-center gap-2 px-2.5 py-1.5 rounded-lg text-red-400 hover:bg-red-500/10 transition-colors cursor-pointer"
              >
                <LogOut className="w-3.5 h-3.5" />
                <span>Log out</span>
              </button>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );

  return (
    <>
      {/* Desktop Sidebar */}
      <aside
        className={`hidden lg:block h-screen sticky top-0 transition-all duration-300 ease-in-out shrink-0 ${
          isCollapsed ? 'w-[72px]' : 'w-64'
        }`}
      >
        {sidebarContent}
      </aside>

      {/* Mobile Drawer Backdrop & Drawer */}
      <AnimatePresence>
        {isMobileOpen && (
          <div className="fixed inset-0 z-50 lg:hidden flex">
            {/* Backdrop */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={onCloseMobile}
              className="fixed inset-0 bg-black/70 backdrop-blur-sm"
            />
            {/* Drawer */}
            <motion.div
              initial={{ x: '-100%' }}
              animate={{ x: 0 }}
              exit={{ x: '-100%' }}
              transition={{ type: 'spring', damping: 25, stiffness: 250 }}
              className="relative w-72 max-w-[85vw] h-full z-10"
            >
              {sidebarContent}
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </>
  );
};
