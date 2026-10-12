import React, { useState } from 'react';
import { ThemeProvider } from './hooks/useTheme';
import { AuthProvider, useAuth } from './hooks/useAuth';
import { IntroScreen } from './pages/IntroScreen';
import { LandingPage } from './pages/LandingPage';
import { AuthPage } from './pages/AuthPage';
import { AppShell } from './pages/AppShell';
import { ResearchRunView } from './pages/ResearchRunView';

function MainAppShell() {
  const { user, logout } = useAuth();
  const [showIntro, setShowIntro] = useState<boolean>(() => {
    // If returning from OAuth redirect, skip intro
    if (window.location.hash.includes('access_token')) {
      sessionStorage.setItem('quorum_intro_seen', 'true');
      return false;
    }
    return !sessionStorage.getItem('quorum_intro_seen');
  });
  const [currentView, setCurrentView] = useState<'landing' | 'auth' | 'app' | 'run'>(() => {
    if (window.location.hash.includes('access_token')) {
      return 'app';
    }
    return 'landing';
  });

  // Auto-switch to workspace when user signs in or completes OAuth redirect
  React.useEffect(() => {
    if (user) {
      if (window.location.hash.includes('access_token') || currentView === 'auth') {
        setCurrentView('app');
      }
    }
  }, [user, currentView]);
  const [forceReplay, setForceReplay] = useState<number>(0);
  const [activeResearchTopic, setActiveResearchTopic] = useState<string>(
    'Compare solid-state batteries vs lithium-ion for grid-scale energy storage'
  );

  const handleReplayIntro = () => {
    sessionStorage.removeItem('quorum_intro_seen');
    setForceReplay((prev) => prev + 1);
    setShowIntro(true);
  };

  const handleAuthSuccess = () => {
    setCurrentView('app');
  };

  const handleSignOut = async () => {
    await logout();
    setCurrentView('landing');
  };

  const handleStartResearch = (query: string, options?: { image?: string | null }) => {
    setActiveResearchTopic(query);
    setCurrentView('run');
  };

  return (
    <div className="min-h-screen bg-[#09090b] text-[#fafafa] selection:bg-white/20 selection:text-white">
      {showIntro ? (
        <IntroScreen
          key={forceReplay}
          onComplete={() => setShowIntro(false)}
          forcePlay={true}
        />
      ) : currentView === 'landing' ? (
        <LandingPage
          onGetStarted={() => setCurrentView('auth')}
          onLogin={() => setCurrentView('auth')}
          onReplayIntro={handleReplayIntro}
        />
      ) : currentView === 'auth' ? (
        <AuthPage
          onBackToLanding={() => setCurrentView('landing')}
          onAuthSuccess={handleAuthSuccess}
        />
      ) : currentView === 'app' ? (
        <AppShell
          onStartResearch={handleStartResearch}
          onSignOut={handleSignOut}
        />
      ) : (
        <ResearchRunView
          topic={activeResearchTopic}
          onNewResearch={() => setCurrentView('app')}
          onBackToWorkspace={() => setCurrentView('app')}
        />
      )}
    </div>
  );
}

export default function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <MainAppShell />
      </AuthProvider>
    </ThemeProvider>
  );
}
