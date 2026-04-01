import React from 'react';
import { premiumTheme } from '../../theme-premium';

const statusConfig = {
  draft: { label: 'Rascunho', color: premiumTheme.text.tertiary, bg: 'rgba(100, 116, 139, 0.2)' },
  sent: { label: 'Enviada', color: premiumTheme.electric.blue, bg: 'rgba(74, 158, 255, 0.2)' },
  viewed: { label: 'Visualizada', color: premiumTheme.electric.cyan, bg: 'rgba(92, 197, 220, 0.2)' },
  partial: { label: 'Parcial', color: premiumTheme.semantic.warning, bg: 'rgba(245, 158, 11, 0.2)' },
  paid: { label: 'Paga', color: premiumTheme.semantic.success, bg: 'rgba(45, 212, 191, 0.2)' },
  overdue: { label: 'Vencida', color: premiumTheme.semantic.danger, bg: 'rgba(239, 68, 68, 0.2)' },
  cancelled: { label: 'Cancelada', color: premiumTheme.text.disabled, bg: 'rgba(71, 85, 105, 0.2)' },
  pending: { label: 'Pendente', color: premiumTheme.semantic.warning, bg: 'rgba(245, 158, 11, 0.2)' },
  approved: { label: 'Aprovado', color: premiumTheme.semantic.success, bg: 'rgba(45, 212, 191, 0.2)' },
  rejected: { label: 'Rejeitado', color: premiumTheme.semantic.danger, bg: 'rgba(239, 68, 68, 0.2)' },
};

export const StatusBadge = ({ status, size = 'md', variant = 'glassmorphic' }) => {
  const config = statusConfig[status] || statusConfig.draft;
  
  const sizeClasses = {
    sm: 'px-2 py-0.5 text-xs',
    md: 'px-3 py-1 text-sm',
    lg: 'px-4 py-1.5 text-base',
  };

  if (variant === 'glassmorphic') {
    return (
      <div
        className={`inline-flex items-center rounded-full font-medium ${sizeClasses[size]}`}
        style={{
          backgroundColor: config.bg,
          color: config.color,
          backdropFilter: 'blur(8px)',
          border: `1px solid ${config.color}40`,
        }}
      >
        {config.label}
      </div>
    );
  }

  return (
    <span
      className={`inline-flex items-center rounded-full font-medium ${sizeClasses[size]}`}
      style={{
        backgroundColor: config.bg,
        color: config.color,
      }}
    >
      {config.label}
    </span>
  );
};