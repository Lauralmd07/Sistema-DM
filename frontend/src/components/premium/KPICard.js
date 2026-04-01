import React from 'react';
import { motion } from 'framer-motion';
import { TrendingUp, TrendingDown } from 'lucide-react';
import { AnimatedNumber } from './AnimatedNumber';
import { GlassCard } from './GlassCard';
import { premiumTheme } from '../../theme-premium';

export const KPICard = ({
  title,
  value,
  format = 'currency',
  change,
  changeLabel = 'vs. mês anterior',
  icon: Icon,
  trend = 'up',
  gradient,
  sparklineData = [],
}) => {
  const isPositive = change >= 0;
  const trendColor = trend === 'up' ? 
    (isPositive ? premiumTheme.semantic.success : premiumTheme.semantic.danger) :
    (isPositive ? premiumTheme.semantic.danger : premiumTheme.semantic.success);

  return (
    <GlassCard hover className="relative overflow-hidden" data-testid={`kpi-card-${title.toLowerCase().replace(/\s+/g, '-')}`}>
      {/* Background gradient glow */}
      {gradient && (
        <div 
          className="absolute inset-0 opacity-10"
          style={{ background: gradient }}
        />
      )}

      <div className="relative z-10">
        {/* Header */}
        <div className="flex items-center justify-between mb-4">
          <span 
            className="text-sm font-medium tracking-wide uppercase"
            style={{ color: premiumTheme.text.secondary }}
          >
            {title}
          </span>
          {Icon && (
            <Icon 
              className="w-5 h-5" 
              style={{ color: premiumTheme.electric.blue }}
            />
          )}
        </div>

        {/* Value */}
        <AnimatedNumber
          value={value}
          format={format}
          className="text-4xl font-light mb-3"
          style={{ color: premiumTheme.text.primary }}
        />

        {/* Change indicator */}
        {change !== undefined && (
          <div className="flex items-center space-x-2">
            <motion.div
              initial={{ scale: 0.8, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              className="flex items-center space-x-1 px-2 py-1 rounded-full"
              style={{
                backgroundColor: `${trendColor}20`,
                color: trendColor,
              }}
            >
              {isPositive ? (
                <TrendingUp className="w-3 h-3" />
              ) : (
                <TrendingDown className="w-3 h-3" />
              )}
              <span className="text-xs font-medium">
                {Math.abs(change).toFixed(1)}%
              </span>
            </motion.div>
            <span className="text-xs" style={{ color: premiumTheme.text.tertiary }}>
              {changeLabel}
            </span>
          </div>
        )}

        {/* Mini sparkline */}
        {sparklineData.length > 0 && (
          <div className="mt-4 h-12">
            <svg width="100%" height="100%" className="overflow-visible">
              <defs>
                <linearGradient id="sparklineGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={premiumTheme.electric.blue} stopOpacity="0.3" />
                  <stop offset="100%" stopColor={premiumTheme.electric.blue} stopOpacity="0" />
                </linearGradient>
              </defs>
              {/* Simple area path - implement based on data */}
            </svg>
          </div>
        )}
      </div>
    </GlassCard>
  );
};