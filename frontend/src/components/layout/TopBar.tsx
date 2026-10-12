import React, { useState } from 'react';
import {
  Search,
  Moon,
  Sun,
  Bell,
  Menu,
  Command,
  Sparkles,
  Check,
} from 'lucide-react';
import { useTheme } from '../../hooks/useTheme';
import { useAuth } from '../../hooks/useAuth';

interface TopBarProps {
  onOpenMobileSidebar: () => void;
  onSearchClick?: () => void;
}

export const TopBar: React.FC<TopBarProps> = ({
  onOpenMobileSidebar,
  onSearchClick,
}) => {
  const { theme, toggleTheme } = useTheme();
  const { user } = useAuth();
  const [showNotifications, setShowNotifications] = useState(false);

  return (
    <header className="sticky top-0 z-30 w-full h-14 bg-[#09090b]/80 backdrop-blur-md border-b border-white/[0.08] px-4 lg:px-8 flex items-center justify-between">
      {/* Left: Mobile hamburger & Context breadcrumb */}
      <div className="flex items-center gap-3">
        <button
          onClick={onOpenMobileSidebar}
          className="lg:hidden p-1.5 rounded-lg text-zinc-400 hover:text-white hover:bg-white/[0.06] transition-colors cursor-pointer"
          title="Open navigation"
        >
          <Menu className="w-5 h-5" />
        </button>

        <div className="flex items-center gap-2 text-xs">
          <span className="text-zinc-500 hidden sm:inline">Quorum</span>
          <span className="text-zinc-600 hidden sm:inline">/</span>
          <span className="text-zinc-200 font-medium">Research Workspace</span>
          <span className="px-1.5 py-0.5 rounded text-[10px] font-mono uppercase bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            Live Swarm
          </span>
        </div>
      </div>

      {/* Center & Right: Search, Theme, Notifications, User Badge */}
      <div className="flex items-center gap-3">
        {/* Search Input / Quick Palette Trigger with ⌘K */}
        <button
          onClick={onSearchClick}
          className="group flex items-center gap-2 px-3 py-1.5 rounded-xl bg-white/[0.04] hover:bg-white/[0.08] border border-white/[0.06] hover:border-white/10 transition-all text-xs text-zinc-400 hover:text-zinc-200 cursor-pointer w-40 sm:w-64"
        >
          <Search className="w-3.5 h-3.5 text-zinc-500 group-hover:text-zinc-300" />
          <span className="flex-1 text-left truncate">Search past research...</span>
          <kbd className="hidden sm:inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded bg-white/[0.06] border border-white/[0.08] text-[10px] font-mono text-zinc-400">
            <Command className="w-2.5 h-2.5" />
            <span>K</span>
          </kbd>
        </button>

        {/* Theme Toggle */}
        <button
          onClick={toggleTheme}
          className="p-2 rounded-xl text-zinc-400 hover:text-white hover:bg-white/[0.06] border border-transparent hover:border-white/[0.06] transition-colors cursor-pointer"
          title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
        >
          {theme === 'dark' ? (
            <Sun className="w-4 h-4 text-zinc-300" />
          ) : (
            <Moon className="w-4 h-4 text-zinc-700" />
          )}
        </button>

        {/* Notifications Bell */}
        <div className="relative">
          <button
            onClick={() => setShowNotifications(!showNotifications)}
            className="relative p-2 rounded-xl text-zinc-400 hover:text-white hover:bg-white/[0.06] border border-transparent hover:border-white/[0.06] transition-colors cursor-pointer"
            title="Notifications"
          >
            <Bell className="w-4 h-4" />
            <span className="absolute top-1.5 right-1.5 w-1.5 h-1.5 rounded-full bg-emerald-400 ring-2 ring-[#09090b]" />
          </button>

          {showNotifications && (
            <div className="absolute right-0 top-full mt-2 w-72 p-3 rounded-2xl bg-[#141518] border border-white/10 shadow-2xl z-50 space-y-2 text-xs">
              <div className="flex items-center justify-between pb-2 border-b border-white/[0.06]">
                <span className="font-semibold text-white">Notifications</span>
                <span className="text-[10px] text-zinc-500">1 new</span>
              </div>
              <div className="p-2 rounded-xl bg-white/[0.03] space-y-1">
                <div className="flex items-center gap-1.5 text-emerald-400 font-medium">
                  <Sparkles className="w-3.5 h-3.5" />
                  <span>Critic Agent Update</span>
                </div>
                <p className="text-zinc-400 text-[11px] leading-relaxed">
                  Quorum v2.4 multi-agent swarm active. Fact-checking citation verification enabled.
                </p>
              </div>
            </div>
          )}
        </div>

        {/* User Status / Pro Badge */}
        <div className="hidden sm:flex items-center gap-2 pl-2 border-l border-white/[0.08]">
          <span className="text-xs text-zinc-300 font-medium truncate max-w-[120px]">
            {user?.name || user?.email?.split('@')[0] || 'Researcher'}
          </span>
          <span className="px-1.5 py-0.5 rounded text-[10px] font-semibold bg-gradient-to-r from-emerald-500/20 to-teal-500/20 text-emerald-300 border border-emerald-500/30">
            PRO
          </span>
        </div>
      </div>
    </header>
  );
};
