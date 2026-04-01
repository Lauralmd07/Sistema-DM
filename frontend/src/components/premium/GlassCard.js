import React from 'react';
import { motion } from 'framer-motion';
import { premiumTheme } from '../../theme-premium';

export const GlassCard = ({ 
  children, 
  className = '', 
  hover = false,
  onClick,
  ...props 
}) => {
  const baseStyles = {
    background: premiumTheme.glass.background,
    backdropFilter: `blur(${premiumTheme.glass.backdropBlur}) saturate(180%)`,
    border: `1px solid ${premiumTheme.glass.borderColor}`,
    boxShadow: premiumTheme.glass.shadow,
  };

  return (
    <motion.div
      className={`rounded-xl p-6 ${className}`}
      style={baseStyles}
      whileHover={hover ? {
        y: -4,
        boxShadow: premiumTheme.shadows.gold,
        borderColor: premiumTheme.border.accent,
      } : undefined}
      transition={{ duration: 0.3, ease: 'easeOut' }}
      onClick={onClick}
      {...props}
    >
      {children}
    </motion.div>
  );
};