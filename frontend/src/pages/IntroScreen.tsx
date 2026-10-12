import React, { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { AnimatedLogo } from '../components/logo/AnimatedLogo';

interface IntroScreenProps {
  onComplete: () => void;
  forcePlay?: boolean;
}

export const IntroScreen: React.FC<IntroScreenProps> = ({ onComplete, forcePlay = false }) => {
  const [isVisible, setIsVisible] = useState(true);

  useEffect(() => {
    // If not forced and user has already seen it this session, skip immediately
    const hasSeen = sessionStorage.getItem('quorum_intro_seen');
    if (hasSeen && !forcePlay) {
      onComplete();
      return;
    }

    // Play ~3.5s total animation before smooth cross-fade
    const timer = setTimeout(() => {
      sessionStorage.setItem('quorum_intro_seen', 'true');
      setIsVisible(false);
      setTimeout(() => {
        onComplete();
      }, 400); // Wait for fade-out transition
    }, 3600);

    return () => clearTimeout(timer);
  }, [onComplete, forcePlay]);

  return (
    <AnimatePresence>
      {isVisible && (
        <motion.div
          key="intro-screen"
          initial={{ opacity: 1 }}
          exit={{ opacity: 0, scale: 0.99, filter: 'blur(4px)' }}
          transition={{ duration: 0.45, ease: 'easeInOut' }}
          className="fixed inset-0 z-50 flex flex-col items-center justify-center bg-[#f4f7f5] dark:bg-[#09090b] text-[#1c2e26] dark:text-[#fafafa] select-none transition-colors"
        >
          <div className="flex flex-col items-center justify-center space-y-6">
            {/* 1. Self-drawing animated logo */}
            <AnimatedLogo size={130} />

            {/* 2. Wordmark fades in below */}
            <motion.div
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 2.2, duration: 0.6, ease: 'easeOut' }}
              className="text-center"
            >
              <h1 className="text-3xl font-semibold tracking-[-0.04em] font-sans text-[#182a22] dark:text-[#f4f4f5]">
                quorum.
              </h1>
            </motion.div>

            {/* 3. Thin linear progress bar (~3.5 seconds) */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 1.0, duration: 0.4 }}
              className="w-36 h-[2px] bg-emerald-950/10 dark:bg-zinc-800 rounded-full overflow-hidden mt-2"
            >
              <motion.div
                className="h-full bg-emerald-900/80 dark:bg-white rounded-full"
                initial={{ width: '0%' }}
                animate={{ width: '100%' }}
                transition={{ delay: 0.5, duration: 3.0, ease: 'easeInOut' }}
              />
            </motion.div>
          </div>

          {/* Subtle click-anywhere to skip hint */}
          <motion.button
            initial={{ opacity: 0 }}
            animate={{ opacity: 0.4 }}
            transition={{ delay: 2.5 }}
            whileHover={{ opacity: 0.8 }}
            onClick={() => {
              sessionStorage.setItem('quorum_intro_seen', 'true');
              setIsVisible(false);
              setTimeout(onComplete, 300);
            }}
            className="absolute bottom-8 text-xs font-mono tracking-wider uppercase text-muted-foreground hover:text-foreground transition-colors cursor-pointer"
          >
            Click to skip
          </motion.button>
        </motion.div>
      )}
    </AnimatePresence>
  );
};
