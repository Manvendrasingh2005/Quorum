import React from 'react';
import { motion } from 'framer-motion';
import { ArrowRight, RotateCcw } from 'lucide-react';
import { QuorumLogo } from '../components/logo/QuorumLogo';

interface LandingPageProps {
  onGetStarted: () => void;
  onLogin: () => void;
  onReplayIntro?: () => void;
}

export const LandingPage: React.FC<LandingPageProps> = ({
  onGetStarted,
  onLogin,
  onReplayIntro,
}) => {
  return (
    <div className="relative min-h-screen w-full bg-[#09090b] text-[#fafafa] flex flex-col justify-between overflow-x-hidden selection:bg-white/20 selection:text-white">
      {/* 1. Moody Dimmed Background Photo & Gradient Mesh */}
      <div className="absolute inset-0 z-0 pointer-events-none overflow-hidden">
        {/* Background photo overlay */}
        <div
          className="absolute inset-0 bg-cover bg-center opacity-30 mix-blend-luminosity scale-105 transition-transform duration-1000"
          style={{ backgroundImage: `url('/assets/landing-bg.png')` }}
        />
        {/* Dark radial and linear gradients for deep moodiness */}
        <div className="absolute inset-0 bg-gradient-to-b from-[#09090b]/80 via-[#09090b]/60 to-[#09090b]" />
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_80%_60%_at_50%_-20%,rgba(120,119,198,0.15),rgba(255,255,255,0))]" />
        <div className="absolute bottom-0 inset-x-0 h-48 bg-gradient-to-t from-[#09090b] to-transparent" />
      </div>

      {/* 2. Minimal Top Nav */}
      <header className="relative z-10 w-full max-w-7xl mx-auto px-6 lg:px-12 py-8 flex items-center justify-between">
        {/* Logo Left */}
        <div className="flex items-center gap-3">
          <div className="text-white hover:opacity-90 transition-opacity cursor-pointer">
            <QuorumLogo size={28} />
          </div>
          <span className="font-semibold text-xl tracking-tight text-white font-sans">
            quorum.
          </span>
        </div>

        {/* Right: Plain Log in + White pill Get started */}
        <div className="flex items-center gap-6">
          {onReplayIntro && (
            <button
              onClick={onReplayIntro}
              title="Replay intro animation"
              className="hidden sm:inline-flex items-center gap-1.5 text-xs text-zinc-400 hover:text-white transition-colors cursor-pointer"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              <span>Intro</span>
            </button>
          )}

          <button
            onClick={onLogin}
            className="text-sm font-medium text-zinc-300 hover:text-white transition-colors cursor-pointer"
          >
            Log in
          </button>

          <button
            onClick={onGetStarted}
            className="group inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-full text-sm font-medium bg-white text-zinc-950 hover:bg-zinc-100 active:scale-[0.98] transition-all cursor-pointer shadow-lg shadow-white/5"
          >
            <span>Get started</span>
            <ArrowRight className="w-4 h-4 transition-transform group-hover:translate-x-0.5" />
          </button>
        </div>
      </header>

      {/* 3. Hero Center Section */}
      <main className="relative z-10 max-w-6xl mx-auto px-6 lg:px-12 py-16 sm:py-24 my-auto flex flex-col items-center text-center">
        <div className="space-y-7 max-w-4xl">
          {/* Subtle multi-agent badge */}
          <motion.div
            initial={{ opacity: 0, y: 14 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.9, delay: 0.1, ease: [0.16, 1, 0.3, 1] }}
            className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full text-xs font-mono tracking-wide uppercase bg-white/[0.06] border border-white/10 text-zinc-300 backdrop-blur-sm"
          >
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
            <span>Autonomous Multi-Agent Swarm</span>
          </motion.div>

          {/* Huge bold white two-line headline with silky smooth staggered reveal */}
          <h1 className="text-5xl sm:text-7xl lg:text-8xl font-bold tracking-[-0.04em] text-white leading-[1.04] overflow-hidden">
            <motion.span
              className="block"
              initial={{ opacity: 0, y: 26, filter: 'blur(6px)' }}
              animate={{ opacity: 1, y: 0, filter: 'blur(0px)' }}
              transition={{ duration: 1.3, delay: 0.25, ease: [0.16, 1, 0.3, 1] }}
            >
              Ask Once.
            </motion.span>
            <motion.span
              className="block text-zinc-200"
              initial={{ opacity: 0, y: 26, filter: 'blur(6px)' }}
              animate={{ opacity: 1, y: 0, filter: 'blur(0px)' }}
              transition={{ duration: 1.3, delay: 0.45, ease: [0.16, 1, 0.3, 1] }}
            >
              Trust Every Claim.
            </motion.span>
          </h1>

          {/* One-line subtext */}
          <motion.p
            initial={{ opacity: 0, y: 18 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 1.2, delay: 0.7, ease: [0.16, 1, 0.3, 1] }}
            className="max-w-2xl mx-auto text-base sm:text-lg lg:text-xl text-zinc-400 font-normal leading-relaxed tracking-tight"
          >
            The multi-agent research engine that plans, searches, fact-checks, and synthesizes cited reports in seconds.
          </motion.p>

          {/* Call-to-actions row */}
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 1.0, delay: 0.9, ease: [0.16, 1, 0.3, 1] }}
            className="pt-3 flex flex-col sm:flex-row items-center justify-center gap-4"
          >
            <button
              onClick={onGetStarted}
              className="group w-full sm:w-auto inline-flex items-center justify-center gap-2.5 px-7 py-3.5 rounded-full text-base font-semibold bg-white text-zinc-950 hover:bg-zinc-100 active:scale-[0.98] transition-all cursor-pointer shadow-xl shadow-white/10"
            >
              <span>Get started</span>
              <ArrowRight className="w-4 h-4 transition-transform group-hover:translate-x-1" />
            </button>

            <button
              onClick={onLogin}
              className="w-full sm:w-auto inline-flex items-center justify-center px-6 py-3.5 rounded-full text-base font-medium text-zinc-300 hover:text-white hover:bg-white/5 active:scale-[0.98] transition-all cursor-pointer"
            >
              Log in
            </button>
          </motion.div>
        </div>
      </main>

      {/* 4. Bottom-Pinned Stats Strip */}
      <motion.footer
        initial={{ opacity: 0, y: 14 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 1.1, delay: 1.0, ease: [0.16, 1, 0.3, 1] }}
        className="relative z-10 w-full border-t border-white/[0.08] bg-[#09090b]/80 backdrop-blur-md"
      >
        <div className="max-w-7xl mx-auto px-6 lg:px-12 py-8">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8 md:gap-12">
            {/* Metric 1 */}
            <div className="flex flex-col items-start md:items-center text-left md:text-center space-y-1">
              <div className="flex items-baseline gap-2">
                <span className="text-3xl sm:text-4xl font-bold tracking-tight text-white font-sans">
                  40%
                </span>
                <span className="text-[10px] font-mono uppercase px-1.5 py-0.5 rounded bg-white/10 text-zinc-400">
                  Placeholder
                </span>
              </div>
              <p className="text-xs font-mono uppercase tracking-widest text-zinc-400">
                Faster Research Synthesis
              </p>
            </div>

            {/* Metric 2 */}
            <div className="flex flex-col items-start md:items-center text-left md:text-center space-y-1 md:border-x md:border-white/[0.08] md:px-6">
              <div className="flex items-baseline gap-2">
                <span className="text-3xl sm:text-4xl font-bold tracking-tight text-white font-sans">
                  3x
                </span>
                <span className="text-[10px] font-mono uppercase px-1.5 py-0.5 rounded bg-white/10 text-zinc-400">
                  Placeholder
                </span>
              </div>
              <p className="text-xs font-mono uppercase tracking-widest text-zinc-400">
                Cross-Examined Citations
              </p>
            </div>

            {/* Metric 3 */}
            <div className="flex flex-col items-start md:items-center text-left md:text-center space-y-1">
              <div className="flex items-baseline gap-2">
                <span className="text-3xl sm:text-4xl font-bold tracking-tight text-white font-sans">
                  12k+
                </span>
                <span className="text-[10px] font-mono uppercase px-1.5 py-0.5 rounded bg-white/10 text-zinc-400">
                  Placeholder
                </span>
              </div>
              <p className="text-xs font-mono uppercase tracking-widest text-zinc-400">
                Claims Verified By Swarm
              </p>
            </div>
          </div>
        </div>
      </motion.footer>
    </div>
  );
};
