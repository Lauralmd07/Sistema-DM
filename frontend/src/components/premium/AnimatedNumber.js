import React, { useEffect, useState } from 'react';
import { motion, useSpring, useTransform } from 'framer-motion';

export const AnimatedNumber = ({ 
  value, 
  format = 'number', 
  className = '',
  duration = 1000,
  prefix = '',
  suffix = ''
}) => {
  const spring = useSpring(0, { 
    duration,
    bounce: 0 
  });
  const display = useTransform(spring, (current) => {
    if (format === 'currency') {
      return `${prefix}R$ ${current.toLocaleString('pt-BR', { 
        minimumFractionDigits: 2,
        maximumFractionDigits: 2 
      })}${suffix}`;
    } else if (format === 'percent') {
      return `${prefix}${current.toFixed(1)}%${suffix}`;
    }
    return `${prefix}${Math.floor(current).toLocaleString('pt-BR')}${suffix}`;
  });

  useEffect(() => {
    spring.set(value);
  }, [spring, value]);

  return <motion.span className={className}>{display}</motion.span>;
};