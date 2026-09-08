import React, { createContext, useContext, useState, useEffect, useCallback, useMemo } from 'react';
import axios from 'axios';

const AuthContext = createContext(null);
export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used within AuthProvider');
  return context;
};

const api = axios.create({
  baseURL: process.env.REACT_APP_API_URL || 'https://sistema-dm.onrender.com/api',
  withCredentials: true,
  headers: { 'Content-Type': 'application/json' },
});

let refreshPromise = null;
api.interceptors.response.use(
  response => response,
  async error => {
    const original = error.config;
    if (error.response?.status !== 401 || !original || original._retry || original.url?.includes('/auth/refresh')) return Promise.reject(error);
    original._retry = true;
    try {
      refreshPromise ||= api.post('/auth/refresh');
      await refreshPromise;
      return api(original);
    } catch (refreshError) {
      return Promise.reject(refreshError);
    } finally {
      refreshPromise = null;
    }
  }
);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const checkAuth = useCallback(async () => {
    try {
      const { data } = await api.get('/auth/me');
      setUser(data);
    } catch {
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { checkAuth(); }, [checkAuth]);

  const login = useCallback(async (email, password) => {
    try {
      setError(null);
      const { data } = await api.post('/auth/login', { email: email.trim().toLowerCase(), password });
      setUser(data);
      return { success: true };
    } catch (err) {
      const errorMsg = err.response?.data?.detail || 'Erro ao fazer login';
      setError(errorMsg);
      return { success: false, error: errorMsg };
    }
  }, []);

  const loginWithGoogle = useCallback(async credential => {
    try {
      setError(null);
      const { data } = await api.post('/auth/google', { credential });
      setUser(data);
      return { success: true };
    } catch (err) {
      const errorMsg = err.response?.data?.detail || 'Não foi possível entrar com o Google';
      setError(errorMsg);
      return { success: false, error: errorMsg };
    }
  }, []);

  const register = useCallback(async (name, email, password) => {
    try {
      setError(null);
      const { data } = await api.post('/auth/register', { name: name.trim(), email: email.trim().toLowerCase(), password });
      setUser(data);
      return { success: true };
    } catch (err) {
      const errorMsg = err.response?.data?.detail || 'Erro ao registrar';
      setError(errorMsg);
      return { success: false, error: errorMsg };
    }
  }, []);

  const logout = useCallback(async () => {
    try { await api.post('/auth/logout'); } catch (_) {}
    setUser(null);
  }, []);

  const value = useMemo(() => ({ user, loading, error, login, loginWithGoogle, register, logout, api }), [user, loading, error, login, loginWithGoogle, register, logout]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export default AuthContext;
