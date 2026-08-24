import React from 'react';
import { HashRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
import { ProtectedRoute } from './components/ProtectedRoute';
import { Login } from './pages/Login';
import { Register } from './pages/Register';
import { Dashboard } from './pages/Dashboard';
import { Agenda } from './pages/Agenda';
import { PrazosAudiencias } from './pages/PrazosAudiencias';
import { Processos } from './pages/Processos';
import { Drive } from './pages/Drive';
import { Clientes } from './pages/Clientes';
import { FinanceiroPremium } from './pages/FinanceiroPremium';
import './App.css';

function App() {
  return (
    <AuthProvider>
      <HashRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/dashboard" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
          <Route path="/agenda" element={<ProtectedRoute><Agenda /></ProtectedRoute>} />
          <Route path="/prazos-audiencias" element={<ProtectedRoute><PrazosAudiencias /></ProtectedRoute>} />
          <Route path="/processos" element={<ProtectedRoute><Processos /></ProtectedRoute>} />
          <Route path="/drive" element={<ProtectedRoute><Drive /></ProtectedRoute>} />
          <Route path="/clientes" element={<ProtectedRoute><Clientes /></ProtectedRoute>} />
          <Route path="/financeiro" element={<ProtectedRoute adminOnly><FinanceiroPremium /></ProtectedRoute>} />
          <Route path="/" element={<Navigate to="/login" replace />} />
          <Route path="*" element={<Navigate to="/login" replace />} />
        </Routes>
      </HashRouter>
    </AuthProvider>
  );
}

export default App;
