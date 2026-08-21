import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
import { ProtectedRoute } from './components/ProtectedRoute';
import { Login } from './pages/Login';
import { Register } from './pages/Register';
import { Dashboard } from './pages/Dashboard';
import { Agenda } from './pages/Agenda';
import { Processos } from './pages/Processos';
import { Drive } from './pages/Drive';
import { FinanceiroPremium } from './pages/FinanceiroPremium';
import './App.css';

const basename = process.env.NODE_ENV === 'production' ? '/Sistema-DM' : '/';

function App() {
  return (
    <AuthProvider>
      <BrowserRouter basename={basename}>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />

          <Route path="/dashboard" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
          <Route path="/agenda" element={<ProtectedRoute><Agenda /></ProtectedRoute>} />
          <Route path="/processos" element={<ProtectedRoute><Processos /></ProtectedRoute>} />
          <Route path="/drive" element={<ProtectedRoute><Drive /></ProtectedRoute>} />
          <Route path="/financeiro" element={<ProtectedRoute><FinanceiroPremium /></ProtectedRoute>} />
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;
