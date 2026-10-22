import React, { useState } from 'react';
import { ThemeProvider } from './hooks/useTheme';
import { AuthProvider, useAuth } from './hooks/useAuth';
import { IntroScreen } from './pages/IntroScreen';
import { LandingPage } from './pages/LandingPage';
import { AuthPage } from './pages/AuthPage';
import { AppShell } from './pages/AppShell';
import { PlanReviewView } from './pages/PlanReviewView';
import { ResearchRunView } from './pages/ResearchRunView';

function MainAppShell() {
  const { user, logout } = useAuth();
  const isOAuthRedirect =
    typeof window !== 'undefined' &&
    (window.location.hash.includes('access_token') ||
      window.location.search.includes('code='));

  const [showIntro, setShowIntro] = useState<boolean>(() => {
    // If returning from OAuth redirect, skip intro
    if (isOAuthRedirect) {
      sessionStorage.setItem('quorum_intro_seen', 'true');
      return false;
    }
    return !sessionStorage.getItem('quorum_intro_seen');
  });
  const [currentView, setCurrentView] = useState<'landing' | 'auth' | 'app' | 'plan' | 'run'>(() => {
    if (isOAuthRedirect) {
      return 'app';
    }
    return 'landing';
  });

  // Auto-switch to workspace when user signs in or completes OAuth redirect
  React.useEffect(() => {
    if (user) {
      if (isOAuthRedirect || currentView === 'auth' || currentView === 'landing') {
        setCurrentView('app');
      }
    }
  }, [user, currentView, isOAuthRedirect]);
  const [forceReplay, setForceReplay] = useState<number>(0);
  const [activeResearchTopic, setActiveResearchTopic] = useState<string>(
    'Compare solid-state batteries vs lithium-ion for grid-scale energy storage'
  );
  const [activeResearchDepth, setActiveResearchDepth] = useState<string>('standard');
  const [planSubquestions, setPlanSubquestions] = useState<string[]>([]);
  const [customSubquestions, setCustomSubquestions] = useState<string[] | undefined>(undefined);

  // Restore topic and depth from shareable permalink if present
  React.useEffect(() => {
    try {
      const searchParams = new URLSearchParams(window.location.search);
      const permalinkTopic = searchParams.get('topic') || searchParams.get('q');
      const permalinkDepth = searchParams.get('depth');
      if (permalinkTopic) {
        setActiveResearchTopic(decodeURIComponent(permalinkTopic));
        if (permalinkDepth && ['flash', 'standard', 'deep'].includes(permalinkDepth)) {
          setActiveResearchDepth(permalinkDepth);
        }
        if (user) {
          setCurrentView('app');
        }
      }
    } catch (e) {
      console.warn('Failed to parse URL query params:', e);
    }
  }, [user]);

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

  const handleStartResearch = (
    query: string,
    options?: { image?: string | null; depth?: string }
  ) => {
    setActiveResearchTopic(query);
    const depth = options?.depth || activeResearchDepth;
    setActiveResearchDepth(depth);
    setCustomSubquestions(undefined);
    setCurrentView('run');
  };

  const handleConfirmPlan = (editedSubquestions: string[]) => {
    setCustomSubquestions(editedSubquestions);
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
      ) : currentView === 'plan' ? (
        <PlanReviewView
          topic={activeResearchTopic}
          subquestions={planSubquestions}
          onConfirm={handleConfirmPlan}
          onBack={() => setCurrentView('app')}
        />
      ) : (
        <ResearchRunView
          topic={activeResearchTopic}
          customSubquestions={customSubquestions}
          depth={activeResearchDepth}
          onNewResearch={() => {
            setCustomSubquestions(undefined);
            setCurrentView('app');
          }}
          onBackToWorkspace={() => {
            setCustomSubquestions(undefined);
            setCurrentView('app');
          }}
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

