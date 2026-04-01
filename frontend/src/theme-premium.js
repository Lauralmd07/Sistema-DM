// Premium "Quiet Luxury" Theme for Legal Management System

export const premiumTheme = {
  // Base colors - Deep Navy Charcoal
  background: {
    primary: '#0A0E17',      // Deep Navy Charcoal
    secondary: '#141922',    // Elevated Surface
    tertiary: '#1C2332',     // Card Background
    quaternary: '#242B3D',   // Hover state
  },
  
  // Accent colors - Matte Brushed Gold
  gold: {
    matte: '#C4A962',        // Primary CTA
    light: '#D4B971',        // Hover state
    dark: '#9C8344',         // Active state
    glow: 'rgba(196, 169, 98, 0.15)', // Subtle backlight
    border: 'rgba(196, 169, 98, 0.08)',
  },
  
  // Electric accents
  electric: {
    blue: '#4A9EFF',         // Electric Blue (data viz)
    cyan: '#5CC5DC',         // Accent highlights
    teal: '#3ECDBD',         // Success states
  },
  
  // Semantic colors
  semantic: {
    success: '#2DD4BF',      // Trust account positive
    warning: '#F59E0B',      // Pending actions
    danger: '#EF4444',       // Overdue payments
    info: '#4A9EFF',         // Information
  },
  
  // Text colors
  text: {
    primary: '#FFFFFF',      // Primary text
    secondary: '#94A3B8',    // Secondary text
    tertiary: '#64748B',     // Tertiary text
    disabled: '#475569',     // Disabled text
  },
  
  // Border colors
  border: {
    primary: 'rgba(255, 255, 255, 0.08)',
    secondary: 'rgba(255, 255, 255, 0.05)',
    accent: 'rgba(196, 169, 98, 0.2)',
  },
  
  // Glassmorphism effects
  glass: {
    background: 'rgba(28, 35, 50, 0.7)',
    backdropBlur: '40px',
    borderColor: 'rgba(196, 169, 98, 0.08)',
    shadow: '0 8px 32px rgba(0, 0, 0, 0.4), inset 0 1px 0 rgba(255, 255, 255, 0.05)',
  },
  
  // Gradients
  gradients: {
    gold: 'linear-gradient(135deg, #C4A962 0%, #9C8344 100%)',
    revenue: 'linear-gradient(135deg, #2DD4BF 0%, #14B8A6 100%)',
    expense: 'linear-gradient(135deg, #EF4444 0%, #DC2626 100%)',
    card: 'linear-gradient(135deg, rgba(28, 35, 50, 0.7) 0%, rgba(20, 25, 34, 0.9) 100%)',
    electric: 'linear-gradient(135deg, #4A9EFF 0%, #3B82F6 100%)',
  },
  
  // Shadows
  shadows: {
    sm: '0 2px 8px rgba(0, 0, 0, 0.15)',
    md: '0 4px 16px rgba(0, 0, 0, 0.2)',
    lg: '0 8px 32px rgba(0, 0, 0, 0.3)',
    xl: '0 12px 48px rgba(0, 0, 0, 0.4)',
    gold: '0 8px 32px rgba(196, 169, 98, 0.2)',
    inset: 'inset 0 1px 0 rgba(255, 255, 255, 0.05)',
  },
  
  // Spacing (8px base)
  spacing: {
    xs: '0.25rem',   // 4px
    sm: '0.5rem',    // 8px
    md: '1rem',      // 16px
    lg: '1.5rem',    // 24px
    xl: '2rem',      // 32px
    '2xl': '3rem',   // 48px
    '3xl': '4rem',   // 64px
  },
  
  // Border radius
  radius: {
    sm: '0.375rem',  // 6px
    md: '0.5rem',    // 8px
    lg: '0.75rem',   // 12px
    xl: '1rem',      // 16px
    full: '9999px',
  },
  
  // Typography
  typography: {
    fontFamily: {
      sans: 'Inter, -apple-system, BlinkMacSystemFont, sans-serif',
      display: 'Playfair Display, Georgia, serif',
      mono: 'JetBrains Mono, monospace',
    },
    fontSize: {
      xs: '0.75rem',    // 12px
      sm: '0.875rem',   // 14px
      base: '1rem',     // 16px
      lg: '1.125rem',   // 18px
      xl: '1.25rem',    // 20px
      '2xl': '1.5rem',  // 24px
      '3xl': '1.875rem',// 30px
      '4xl': '2.25rem', // 36px
      '5xl': '3rem',    // 48px
    },
    fontWeight: {
      light: 300,
      normal: 400,
      medium: 500,
      semibold: 600,
      bold: 700,
    },
    lineHeight: {
      tight: 1.25,
      normal: 1.5,
      relaxed: 1.75,
    },
    letterSpacing: {
      tight: '-0.025em',
      normal: '0',
      wide: '0.025em',
      wider: '0.05em',
    },
  },
  
  // Transitions
  transitions: {
    fast: '150ms cubic-bezier(0.4, 0, 0.2, 1)',
    base: '300ms cubic-bezier(0.4, 0, 0.2, 1)',
    slow: '500ms cubic-bezier(0.4, 0, 0.2, 1)',
    spring: '400ms cubic-bezier(0.34, 1.56, 0.64, 1)',
  },
  
  // Z-index layers
  zIndex: {
    dropdown: 1000,
    sticky: 1020,
    fixed: 1030,
    modalBackdrop: 1040,
    modal: 1050,
    popover: 1060,
    tooltip: 1070,
  },
};

// CSS-in-JS helper functions
export const glassEffect = (theme = premiumTheme) => ({
  background: theme.glass.background,
  backdropFilter: `blur(${theme.glass.backdropBlur}) saturate(180%)`,
  border: `1px solid ${theme.glass.borderColor}`,
  boxShadow: theme.glass.shadow,
});

export const hoverEffect = (theme = premiumTheme) => ({
  transform: 'translateY(-2px)',
  boxShadow: theme.shadows.gold,
  borderColor: theme.border.accent,
  transition: theme.transitions.base,
});

export const goldGradientText = (theme = premiumTheme) => ({
  background: theme.gradients.gold,
  WebkitBackgroundClip: 'text',
  WebkitTextFillColor: 'transparent',
  backgroundClip: 'text',
});
