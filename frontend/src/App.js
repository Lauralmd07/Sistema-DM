import React from 'react';

import {
  BrowserRouter,
  Routes,
  Route,
  Navigate,
} from 'react-router-dom';

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

// ==================== APP ====================

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>

        <Routes>

          {/* ==================== PUBLIC ==================== */}

          <Route
            path="/login"
            element={<Login />}
          />

          <Route
            path="/register"
            element={<Register />}
          />

          {/* ==================== PROTECTED ==================== */}

          <Route
            path="/"
            element={
              <ProtectedRoute>
                <Navigate to="/dashboard" replace />
              </ProtectedRoute>
            }
          />

          <Route
            path="/dashboard"
            element={
              <ProtectedRoute>
                <Dashboard />
              </ProtectedRoute>
            }
          />

          <Route
            path="/agenda"
            element={
              <ProtectedRoute>
                <Agenda />
              </ProtectedRoute>
            }
          />

          <Route
            path="/processos"
            element={
              <ProtectedRoute>
                <Processos />
              </ProtectedRoute>
            }
          />

          <Route
            path="/drive"
            element={
              <ProtectedRoute>
                <Drive />
              </ProtectedRoute>
            }
          />

          <Route
            path="/financeiro"
            element={
              <ProtectedRoute>
                <FinanceiroPremium />
              </ProtectedRoute>
            }
          />

          {/* ==================== FALLBACK ==================== */}

          <Route
            path="*"
            element={<Navigate to="/" replace />}
          />

        </Routes>

      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;
