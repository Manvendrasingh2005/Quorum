import React from 'react';
import { motion } from 'framer-motion';

interface AnimatedLogoProps {
  size?: number;
  className?: string;
}

export const AnimatedLogo: React.FC<AnimatedLogoProps> = ({ size = 120, className = '' }) => {
  return (
    <div className={`relative flex items-center justify-center ${className}`}>
      <svg
        width={size}
        height={size}
        viewBox="0 0 120 120"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className="overflow-visible"
      >
        <defs>
          <filter id="center-glow" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="3" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        {/* 1. Outer Ring: Traces itself first */}
        <motion.circle
          cx="60"
          cy="60"
          r="42"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          className="text-emerald-950/80 dark:text-zinc-300"
          initial={{ pathLength: 0, opacity: 0 }}
          animate={{ pathLength: 1, opacity: 0.9 }}
          transition={{ duration: 0.9, ease: 'easeInOut' }}
        />

        {/* 2. Spokes: Draw from center to the 4 nodes */}
        {/* Top Spoke */}
        <motion.line
          x1="60"
          y1="60"
          x2="60"
          y2="18"
          stroke="currentColor"
          strokeWidth="1.5"
          className="text-emerald-900/60 dark:text-zinc-400/60"
          initial={{ pathLength: 0 }}
          animate={{ pathLength: 1 }}
          transition={{ delay: 0.8, duration: 0.45, ease: 'easeOut' }}
        />
        {/* Right Spoke */}
        <motion.line
          x1="60"
          y1="60"
          x2="102"
          y2="60"
          stroke="currentColor"
          strokeWidth="1.5"
          className="text-emerald-900/60 dark:text-zinc-400/60"
          initial={{ pathLength: 0 }}
          animate={{ pathLength: 1 }}
          transition={{ delay: 0.85, duration: 0.45, ease: 'easeOut' }}
        />
        {/* Bottom Spoke */}
        <motion.line
          x1="60"
          y1="60"
          x2="60"
          y2="102"
          stroke="currentColor"
          strokeWidth="1.5"
          className="text-emerald-900/60 dark:text-zinc-400/60"
          initial={{ pathLength: 0 }}
          animate={{ pathLength: 1 }}
          transition={{ delay: 0.9, duration: 0.45, ease: 'easeOut' }}
        />
        {/* Left Spoke */}
        <motion.line
          x1="60"
          y1="60"
          x2="18"
          y2="60"
          stroke="currentColor"
          strokeWidth="1.5"
          className="text-emerald-900/60 dark:text-zinc-400/60"
          initial={{ pathLength: 0 }}
          animate={{ pathLength: 1 }}
          transition={{ delay: 0.95, duration: 0.45, ease: 'easeOut' }}
        />

        {/* Subtle geometric overlapping agent loops from reference screenshot */}
        <motion.circle
          cx="60"
          cy="46"
          r="22"
          stroke="currentColor"
          strokeWidth="1.5"
          className="text-emerald-900/50 dark:text-zinc-400/40"
          initial={{ pathLength: 0, opacity: 0 }}
          animate={{ pathLength: 1, opacity: 0.6 }}
          transition={{ delay: 0.7, duration: 0.8, ease: 'easeInOut' }}
        />
        <motion.circle
          cx="74"
          cy="60"
          r="22"
          stroke="currentColor"
          strokeWidth="1.5"
          className="text-emerald-900/50 dark:text-zinc-400/40"
          initial={{ pathLength: 0, opacity: 0 }}
          animate={{ pathLength: 1, opacity: 0.6 }}
          transition={{ delay: 0.75, duration: 0.8, ease: 'easeInOut' }}
        />
        <motion.circle
          cx="60"
          cy="74"
          r="22"
          stroke="currentColor"
          strokeWidth="1.5"
          className="text-emerald-900/50 dark:text-zinc-400/40"
          initial={{ pathLength: 0, opacity: 0 }}
          animate={{ pathLength: 1, opacity: 0.6 }}
          transition={{ delay: 0.8, duration: 0.8, ease: 'easeInOut' }}
        />
        <motion.circle
          cx="46"
          cy="60"
          r="22"
          stroke="currentColor"
          strokeWidth="1.5"
          className="text-emerald-900/50 dark:text-zinc-400/40"
          initial={{ pathLength: 0, opacity: 0 }}
          animate={{ pathLength: 1, opacity: 0.6 }}
          transition={{ delay: 0.85, duration: 0.8, ease: 'easeInOut' }}
        />

        {/* 3. Four Nodes: Pop in one by one */}
        {/* Node 1: Top (Planner) */}
        <motion.circle
          cx="60"
          cy="18"
          r="4.5"
          fill="currentColor"
          className="text-emerald-800 dark:text-indigo-400"
          initial={{ scale: 0, opacity: 0 }}
          animate={{ scale: [0, 1.3, 1], opacity: 1 }}
          transition={{ delay: 1.3, duration: 0.35, ease: 'backOut' }}
        />
        {/* Node 2: Right (Researcher) */}
        <motion.circle
          cx="102"
          cy="60"
          r="4.5"
          fill="currentColor"
          className="text-emerald-800 dark:text-emerald-400"
          initial={{ scale: 0, opacity: 0 }}
          animate={{ scale: [0, 1.3, 1], opacity: 1 }}
          transition={{ delay: 1.5, duration: 0.35, ease: 'backOut' }}
        />
        {/* Node 3: Bottom (Critic) */}
        <motion.circle
          cx="60"
          cy="102"
          r="4.5"
          fill="currentColor"
          className="text-emerald-800 dark:text-amber-400"
          initial={{ scale: 0, opacity: 0 }}
          animate={{ scale: [0, 1.3, 1], opacity: 1 }}
          transition={{ delay: 1.7, duration: 0.35, ease: 'backOut' }}
        />
        {/* Node 4: Left (Writer) */}
        <motion.circle
          cx="18"
          cy="60"
          r="4.5"
          fill="currentColor"
          className="text-emerald-800 dark:text-purple-400"
          initial={{ scale: 0, opacity: 0 }}
          animate={{ scale: [0, 1.3, 1], opacity: 1 }}
          transition={{ delay: 1.9, duration: 0.35, ease: 'backOut' }}
        />

        {/* 4. Center Glowing Point: Pulses once */}
        <motion.circle
          cx="60"
          cy="60"
          r="4"
          fill="currentColor"
          filter="url(#center-glow)"
          className="text-emerald-900 dark:text-white"
          initial={{ scale: 0, opacity: 0 }}
          animate={{
            scale: [0, 1, 2.2, 1],
            opacity: [0, 0.8, 1, 0.9],
          }}
          transition={{
            delay: 2.25,
            duration: 0.6,
            times: [0, 0.2, 0.6, 1],
            ease: 'easeOut',
          }}
        />
      </svg>
    </div>
  );
};
