import React, { createContext, useContext, useState, useEffect } from 'react';
import axios from 'axios';

const AuthContext = createContext(null);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
};

const api = axios.create({
  baseURL: `${process.env.REACT_APP_BACKEND_URL}/api`,
  withCredentials: true,
});

function formatApiErrorDetail(detail) {
  if (detail == null) return "Algo deu errado. Por favor, tente novamente.";
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail))
    return detail.map((e) => (e && typeof e.msg === "string" ? e.msg : JSON.stringify(e))).filter(Boolean).join(" ");
  if (detail && typeof detail.msg === "string") return detail.msg;
  return String(detail);
}

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    checkAuth();
  }, []);

  const checkAuth = async () => {
    try {
      const { data } = await api.get('/auth/me');
      setUser(data);
    } catch (err) {
      setUser(false);
    } finally {
      setLoading(false);
    }
  };

  const login = async (email, password) => {
    try {
      setError(null);
      const { data } = await api.post('/auth/login', { email, password });
      setUser(data);
      return { success: true };
    } catch (err) {
      const errorMsg = formatApiErrorDetail(err.response?.data?.detail) || err.message;
      setError(errorMsg);
      return { success: false, error: errorMsg };
    }
  };

  const register = async (name, email, password, role = 'lawyer') => {
    try {
      setError(null);
      const { data } = await api.post('/auth/register', { name, email, password, role });
      setUser(data);
      return { success: true };
    } catch (err) {
      const errorMsg = formatApiErrorDetail(err.response?.data?.detail) || err.message;
      setError(errorMsg);
      return { success: false, error: errorMsg };
    }
  };

  const logout = async () => {
    try {
      await api.post('/auth/logout');
      setUser(false);
    } catch (err) {
      console.error('Logout error:', err);
      setUser(false);
    }
  };

  const value = {
    user,
    loading,
    error,
    login,
    register,
    logout,
    api,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};
