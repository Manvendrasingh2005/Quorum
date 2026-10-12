import React from 'react';

interface QuorumLogoProps {
  className?: string;
  size?: number;
}

export const QuorumLogo: React.FC<QuorumLogoProps> = ({ className = 'text-foreground', size = 32 }) => {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 100 100"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
    >
      {/* Outer bounding circle */}
      <circle cx="50" cy="50" r="38" stroke="currentColor" strokeWidth="2.5" opacity="0.4" />
      {/* 4 Intersecting Agent Rings (Planner, Researcher, Critic, Writer) */}
      <circle cx="50" cy="38" r="18" stroke="currentColor" strokeWidth="2" opacity="0.85" />
      <circle cx="62" cy="50" r="18" stroke="currentColor" strokeWidth="2" opacity="0.85" />
      <circle cx="50" cy="62" r="18" stroke="currentColor" strokeWidth="2" opacity="0.85" />
      <circle cx="38" cy="50" r="18" stroke="currentColor" strokeWidth="2" opacity="0.85" />
      {/* Center glowing focal point */}
      <circle cx="50" cy="50" r="3.5" fill="currentColor" />
    </svg>
  );
};
