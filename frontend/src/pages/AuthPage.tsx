import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  CheckCircle2,
  AlertCircle,
  ArrowLeft,
  Eye,
  EyeOff,
  Loader2,
  Sparkles,
  ShieldCheck,
  Search,
  FileText,
} from 'lucide-react';
import { useAuth } from '../hooks/useAuth';
import { isSupabaseConfigured } from '../lib/supabase';
import { QuorumLogo } from '../components/logo/QuorumLogo';

interface AuthPageProps {
  onBackToLanding: () => void;
  onAuthSuccess: () => void;
}

type AuthMode = 'signin' | 'signup' | 'forgot';

export const AuthPage: React.FC<AuthPageProps> = ({ onBackToLanding, onAuthSuccess }) => {
  const { login, signup, loginWithGoogle, resetPassword } = useAuth();

  const [mode, setMode] = useState<AuthMode>('signin');
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);

  const [isLoading, setIsLoading] = useState(false);
  const [isGoogleLoading, setIsGoogleLoading] = useState(false);
  const [generalError, setGeneralError] = useState<string | null>(null);
  const [emailError, setEmailError] = useState<string | null>(null);
  const [passwordError, setPasswordError] = useState<string | null>(null);
  const [nameError, setNameError] = useState<string | null>(null);
  const [resetSent, setResetSent] = useState(false);

  const validate = (): boolean => {
    let isValid = true;
    setEmailError(null);
    setPasswordError(null);
    setNameError(null);
    setGeneralError(null);

    // Email validation
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!email.trim()) {
      setEmailError('Email address is required. Please enter your work or personal email.');
      isValid = false;
    } else if (!emailRegex.test(email.trim())) {
      setEmailError('Invalid email format. Please make sure to include an "@" and valid domain (e.g. name@domain.com).');
      isValid = false;
    }

    // Name validation for signup
    if (mode === 'signup' && !name.trim()) {
      setNameError('Full name is required. Please tell us your name.');
      isValid = false;
    }

    // Password validation
    if (mode !== 'forgot') {
      if (!password) {
        setPasswordError('Password is required.');
        isValid = false;
      } else if (mode === 'signin' && password.length < 6) {
        setPasswordError('Password must be at least 6 characters long.');
        isValid = false;
      } else if (mode === 'signup' && password.length < 8) {
        setPasswordError('Password is too short. Please choose a password with at least 8 characters for security.');
        isValid = false;
      }
    }

    return isValid;
  };

  const handleGoogleLogin = async () => {
    try {
      setIsGoogleLoading(true);
      setGeneralError(null);
      const res = await loginWithGoogle();
      if (res?.error) {
        setGeneralError(res.error);
        setIsGoogleLoading(false);
      } else if (!isSupabaseConfigured) {
        onAuthSuccess();
        setIsGoogleLoading(false);
      }
      // If isSupabaseConfigured is true, browser redirects to Google OAuth; keep isGoogleLoading active
    } catch {
      setGeneralError('Unable to authenticate with Google. Please try email sign-in or check connection.');
      setIsGoogleLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validate()) return;

    setIsLoading(true);
    setGeneralError(null);

    try {
      if (mode === 'signin') {
        const res = await login(email, password);
        if (res.error) {
          setGeneralError(res.error);
        } else {
          onAuthSuccess();
        }
      } else if (mode === 'signup') {
        const res = await signup(name, email, password);
        if (res.error) {
          setGeneralError(res.error);
        } else {
          onAuthSuccess();
        }
      } else if (mode === 'forgot') {
        await resetPassword(email);
        setResetSent(true);
      }
    } catch {
      setGeneralError('An unexpected authentication error occurred. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen w-full bg-[#09090b] text-[#fafafa] flex flex-col lg:grid lg:grid-cols-12 selection:bg-white/20 selection:text-white">
      {/* ================= LEFT BRAND PANEL (Desktop 5 cols) ================= */}
      <div className="relative hidden lg:flex lg:col-span-5 xl:col-span-5 flex-col justify-between p-12 bg-[#0c0d0f] border-r border-white/[0.08] overflow-hidden">
        {/* Subtle background ambient mesh */}
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_20%_30%,rgba(99,102,241,0.08),transparent_70%)] pointer-events-none" />
        <div className="absolute -bottom-24 -left-24 w-96 h-96 bg-emerald-500/5 rounded-full blur-3xl pointer-events-none" />

        {/* Top: Logo & Back Link */}
        <div className="relative z-10 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <QuorumLogo size={30} className="text-white" />
            <span className="font-semibold text-xl tracking-tight text-white font-sans">
              quorum.
            </span>
          </div>

          <button
            onClick={onBackToLanding}
            className="inline-flex items-center gap-1.5 text-xs text-zinc-400 hover:text-white transition-colors cursor-pointer"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Back to home</span>
          </button>
        </div>

        {/* Center: Hero Statement & 3-item Feature Checklist */}
        <div className="relative z-10 my-auto py-8 space-y-8 max-w-md">
          <div className="space-y-4">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-mono uppercase bg-white/[0.06] border border-white/10 text-zinc-300">
              <Sparkles className="w-3.5 h-3.5 text-emerald-400" />
              <span>Multi-Agent Swarm Intelligence</span>
            </div>

            <h2 className="text-3xl xl:text-4xl font-bold tracking-tight text-white leading-tight">
              Four specialized agents. <br />
              <span className="text-zinc-300">One verified truth.</span>
            </h2>

            <p className="text-sm text-zinc-400 leading-relaxed">
              Eliminate hallucinations. Quorum orchestrates Planner, Researcher, Critic, and Writer agents to produce rigorous, cited intelligence.
            </p>
          </div>

          {/* 3-Item Feature Checklist */}
          <div className="space-y-4 pt-2">
            <div className="flex items-start gap-3.5">
              <div className="p-1 rounded-md bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 mt-0.5">
                <Search className="w-4 h-4" />
              </div>
              <div className="space-y-0.5">
                <h4 className="text-sm font-semibold text-white">Autonomous Investigation</h4>
                <p className="text-xs text-zinc-400 leading-normal">
                  Deconstructs complex research queries into structured sub-topics and primary sources.
                </p>
              </div>
            </div>

            <div className="flex items-start gap-3.5">
              <div className="p-1 rounded-md bg-amber-500/10 text-amber-400 border border-amber-500/20 mt-0.5">
                <ShieldCheck className="w-4 h-4" />
              </div>
              <div className="space-y-0.5">
                <h4 className="text-sm font-semibold text-white">Adversarial Critic Loop</h4>
                <p className="text-xs text-zinc-400 leading-normal">
                  Rejects unsupported assertions and sends drafts back until citations are confirmed.
                </p>
              </div>
            </div>

            <div className="flex items-start gap-3.5">
              <div className="p-1 rounded-md bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 mt-0.5">
                <FileText className="w-4 h-4" />
              </div>
              <div className="space-y-0.5">
                <h4 className="text-sm font-semibold text-white">Export-Ready Cited Briefs</h4>
                <p className="text-xs text-zinc-400 leading-normal">
                  Synthesizes clean markdown reports with verifiable footnote links and executive summaries.
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Bottom: Social Proof Footer */}
        <div className="relative z-10 pt-6 border-t border-white/[0.06] flex items-center gap-3">
          <div className="flex -space-x-2">
            <img
              className="w-7 h-7 rounded-full border border-zinc-900 object-cover"
              src="https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=100&h=100&fit=crop&crop=faces"
              alt="User avatar"
            />
            <img
              className="w-7 h-7 rounded-full border border-zinc-900 object-cover"
              src="https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=100&h=100&fit=crop&crop=faces"
              alt="User avatar"
            />
            <img
              className="w-7 h-7 rounded-full border border-zinc-900 object-cover"
              src="https://images.unsplash.com/photo-1492562080023-ab3db95bfbce?w=100&h=100&fit=crop&crop=faces"
              alt="User avatar"
            />
          </div>
          <span className="text-xs text-zinc-400 font-medium">
            Trusted by research teams, founders, and analysts
          </span>
        </div>
      </div>

      {/* ================= RIGHT CARD PANEL (7 cols) ================= */}
      <div className="flex-1 lg:col-span-7 xl:col-span-7 flex flex-col justify-center items-center px-6 py-12 lg:px-16">
        {/* Mobile top bar */}
        <div className="w-full max-w-md lg:hidden flex items-center justify-between mb-8">
          <div className="flex items-center gap-2">
            <QuorumLogo size={26} className="text-white" />
            <span className="font-semibold text-lg tracking-tight text-white">quorum.</span>
          </div>
          <button
            onClick={onBackToLanding}
            className="inline-flex items-center gap-1 text-xs text-zinc-400 hover:text-white"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Home</span>
          </button>
        </div>

        <motion.div
          layout
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
          className="w-full max-w-md space-y-6"
        >
          {/* Card Header */}
          <div className="space-y-2 text-left">
            <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-white">
              {mode === 'signin' && 'Welcome back'}
              {mode === 'signup' && 'Create your account'}
              {mode === 'forgot' && 'Reset your password'}
            </h1>
            <p className="text-sm text-zinc-400">
              {mode === 'signin' && 'Sign in to access your autonomous research runs and saved reports.'}
              {mode === 'signup' && 'Join Quorum to explore multi-agent intelligence and fact-checked synthesis.'}
              {mode === 'forgot' && 'Enter your verified account email address to receive recovery instructions.'}
            </p>
          </div>

          {/* Google OAuth Simulation Button */}
          {mode !== 'forgot' && (
            <div className="space-y-4">
              <button
                type="button"
                onClick={handleGoogleLogin}
                disabled={isLoading || isGoogleLoading}
                className="w-full inline-flex items-center justify-center gap-3 px-4 py-3 rounded-xl border border-white/10 bg-white/[0.04] hover:bg-white/[0.08] active:scale-[0.99] transition-all text-sm font-medium text-white cursor-pointer disabled:opacity-50 shadow-sm"
              >
                {isGoogleLoading ? (
                  <Loader2 className="w-4 h-4 animate-spin text-zinc-400" />
                ) : (
                  <svg className="w-4 h-4" viewBox="0 0 24 24">
                    <path
                      fill="#4285F4"
                      d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                    />
                    <path
                      fill="#34A853"
                      d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                    />
                    <path
                      fill="#FBBC05"
                      d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"
                    />
                    <path
                      fill="#EA4335"
                      d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"
                    />
                  </svg>
                )}
                <span>{isGoogleLoading ? 'Connecting to Google...' : 'Continue with Google'}</span>
              </button>

              {/* Divider */}
              <div className="relative flex items-center justify-center">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t border-white/[0.08]" />
                </div>
                <span className="relative px-3 bg-[#09090b] text-[11px] font-mono uppercase tracking-wider text-zinc-500">
                  Or continue with email
                </span>
              </div>
            </div>
          )}

          {/* General Error Banner */}
          <AnimatePresence>
            {generalError && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                className="p-3.5 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-xs flex items-start gap-2.5"
              >
                <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
                <div className="space-y-0.5">
                  <p className="font-medium">Authentication Failed</p>
                  <p className="text-red-400/80">{generalError}</p>
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Reset Link Success Banner */}
          <AnimatePresence>
            {resetSent && (
              <motion.div
                initial={{ opacity: 0, scale: 0.98 }}
                animate={{ opacity: 1, scale: 1 }}
                className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs flex items-start gap-2.5"
              >
                <CheckCircle2 className="w-4 h-4 shrink-0 mt-0.5" />
                <div className="space-y-1">
                  <p className="font-semibold text-sm">Recovery email dispatched</p>
                  <p className="text-emerald-400/80">
                    We sent password reset instructions to <strong>{email}</strong>. Please check your inbox and spam folder.
                  </p>
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Form */}
          {!resetSent && (
            <form onSubmit={handleSubmit} className="space-y-4">
              {/* Full Name (Sign Up only) */}
              {mode === 'signup' && (
                <div className="space-y-1.5 text-left">
                  <label className="text-xs font-medium text-zinc-300">
                    Full Name
                  </label>
                  <input
                    type="text"
                    value={name}
                    onChange={(e) => {
                      setName(e.target.value);
                      if (nameError) setNameError(null);
                    }}
                    placeholder="Jane Doe"
                    className={`w-full px-3.5 py-2.5 rounded-xl bg-white/[0.04] border ${
                      nameError ? 'border-red-500/50 focus:border-red-500' : 'border-white/10 focus:border-white/30'
                    } text-sm text-white placeholder-zinc-500 outline-none transition-colors`}
                  />
                  {nameError && (
                    <p className="text-[11px] text-red-400 flex items-center gap-1.5 mt-1">
                      <AlertCircle className="w-3 h-3 shrink-0" />
                      <span>{nameError}</span>
                    </p>
                  )}
                </div>
              )}

              {/* Email Address */}
              <div className="space-y-1.5 text-left">
                <label className="text-xs font-medium text-zinc-300">
                  Email Address
                </label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => {
                    setEmail(e.target.value);
                    if (emailError) setEmailError(null);
                  }}
                  placeholder="name@company.com"
                  className={`w-full px-3.5 py-2.5 rounded-xl bg-white/[0.04] border ${
                    emailError ? 'border-red-500/50 focus:border-red-500' : 'border-white/10 focus:border-white/30'
                  } text-sm text-white placeholder-zinc-500 outline-none transition-colors`}
                />
                {emailError && (
                  <p className="text-[11px] text-red-400 flex items-center gap-1.5 mt-1">
                    <AlertCircle className="w-3 h-3 shrink-0" />
                    <span>{emailError}</span>
                  </p>
                )}
              </div>

              {/* Password (Sign In & Sign Up only) */}
              {mode !== 'forgot' && (
                <div className="space-y-1.5 text-left">
                  <div className="flex items-center justify-between">
                    <label className="text-xs font-medium text-zinc-300">
                      Password
                    </label>
                    {mode === 'signin' && (
                      <button
                        type="button"
                        onClick={() => {
                          setMode('forgot');
                          setGeneralError(null);
                        }}
                        className="text-xs text-zinc-400 hover:text-white transition-colors cursor-pointer"
                      >
                        Forgot password?
                      </button>
                    )}
                  </div>

                  <div className="relative">
                    <input
                      type={showPassword ? 'text' : 'password'}
                      value={password}
                      onChange={(e) => {
                        setPassword(e.target.value);
                        if (passwordError) setPasswordError(null);
                      }}
                      placeholder="••••••••••••"
                      className={`w-full px-3.5 py-2.5 pr-10 rounded-xl bg-white/[0.04] border ${
                        passwordError ? 'border-red-500/50 focus:border-red-500' : 'border-white/10 focus:border-white/30'
                      } text-sm text-white placeholder-zinc-500 outline-none transition-colors`}
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-zinc-400 hover:text-white transition-colors cursor-pointer"
                    >
                      {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  </div>

                  {passwordError && (
                    <p className="text-[11px] text-red-400 flex items-center gap-1.5 mt-1">
                      <AlertCircle className="w-3 h-3 shrink-0" />
                      <span>{passwordError}</span>
                    </p>
                  )}
                </div>
              )}

              {/* Submit CTA Button */}
              <button
                type="submit"
                disabled={isLoading}
                className="w-full mt-2 inline-flex items-center justify-center gap-2 px-4 py-3 rounded-xl bg-white text-zinc-950 hover:bg-zinc-100 active:scale-[0.99] transition-all text-sm font-semibold cursor-pointer disabled:opacity-50 shadow-md shadow-white/5"
              >
                {isLoading && <Loader2 className="w-4 h-4 animate-spin text-zinc-700" />}
                <span>
                  {mode === 'signin' && 'Sign in to Quorum'}
                  {mode === 'signup' && 'Create your account'}
                  {mode === 'forgot' && 'Send reset instructions'}
                </span>
              </button>
            </form>
          )}

          {/* Mode Switching Footer */}
          <div className="pt-2 text-center text-xs text-zinc-400 space-y-2">
            {mode === 'signin' && (
              <p>
                Don't have an account yet?{' '}
                <button
                  type="button"
                  onClick={() => {
                    setMode('signup');
                    setGeneralError(null);
                  }}
                  className="font-medium text-white underline underline-offset-4 hover:text-zinc-200 cursor-pointer"
                >
                  Create one now
                </button>
              </p>
            )}

            {mode === 'signup' && (
              <p>
                Already have an account?{' '}
                <button
                  type="button"
                  onClick={() => {
                    setMode('signin');
                    setGeneralError(null);
                  }}
                  className="font-medium text-white underline underline-offset-4 hover:text-zinc-200 cursor-pointer"
                >
                  Sign in
                </button>
              </p>
            )}

            {mode === 'forgot' && (
              <p>
                Remembered your password?{' '}
                <button
                  type="button"
                  onClick={() => {
                    setMode('signin');
                    setResetSent(false);
                    setGeneralError(null);
                  }}
                  className="font-medium text-white underline underline-offset-4 hover:text-zinc-200 cursor-pointer"
                >
                  Back to sign in
                </button>
              </p>
            )}

            {mode === 'signup' && (
              <p className="text-[11px] text-zinc-500 pt-2 leading-relaxed">
                By continuing, you acknowledge Quorum's research terms and strict data privacy safeguards.
              </p>
            )}
          </div>
        </motion.div>
      </div>
    </div>
  );
};
