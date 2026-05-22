// src/contexts/AuthContext.js

import React, {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
} from 'react';

import axios from 'axios';

// ==================== API ====================

const API_URL =
  process.env.REACT_APP_API_URL ||
  'https://sistema-dm.onrender.com/api';

export const api = axios.create({
  baseURL: API_URL,
  withCredentials: true,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// ==================== CONTEXT ====================

const AuthContext = createContext(null);

// ==================== PROVIDER ====================

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);

  const [loading, setLoading] = useState(true);

  const [authLoading, setAuthLoading] = useState(false);

  // ==================== LOAD USER ====================

  const loadUser = useCallback(async () => {
    try {
      const response = await api.get('/auth/me');

      setUser(response.data);

      return response.data;
    } catch (error) {
      setUser(null);

      return null;
    }
  }, []);

  // ==================== LOGIN ====================

  const login = async (email, password) => {
    try {
      setAuthLoading(true);

      const response = await api.post('/auth/login', {
        email,
        password,
      });

      setUser(response.data);

      return {
        success: true,
        user: response.data,
      };
    } catch (error) {
      console.error('Erro no login:', error);

      return {
        success: false,
        error:
          error?.response?.data?.detail ||
          'Erro ao realizar login',
      };
    } finally {
      setAuthLoading(false);
    }
  };

  // ==================== REGISTER ====================

  const register = async ({
    name,
    email,
    password,
    role = 'lawyer',
  }) => {
    try {
      setAuthLoading(true);

      const response = await api.post('/auth/register', {
        name,
        email,
        password,
        role,
      });

      setUser(response.data);

      return {
        success: true,
        user: response.data,
      };
    } catch (error) {
      console.error('Erro no cadastro:', error);

      return {
        success: false,
        error:
          error?.response?.data?.detail ||
          'Erro ao criar conta',
      };
    } finally {
      setAuthLoading(false);
    }
  };

  // ==================== LOGOUT ====================

  const logout = async () => {
    try {
      await api.post('/auth/logout');
    } catch (error) {
      console.error('Erro no logout:', error);
    } finally {
      setUser(null);
    }
  };

  // ==================== CHECK AUTH ====================

  useEffect(() => {
    const initAuth = async () => {
      try {
        await loadUser();
      } finally {
        setLoading(false);
      }
    };

    initAuth();
  }, [loadUser]);

  // ==================== AXIOS INTERCEPTOR ====================

  useEffect(() => {
    const responseInterceptor = api.interceptors.response.use(
      (response) => response,

      async (error) => {
        if (error?.response?.status === 401) {
          setUser(null);
        }

        return Promise.reject(error);
      }
    );

    return () => {
      api.interceptors.response.eject(responseInterceptor);
    };
  }, []);

  // ==================== CONTEXT VALUE ====================

  const value = {
    user,
    setUser,

    loading,
    authLoading,

    authenticated: !!user,

    login,
    register,
    logout,

    loadUser,

    api,
  };

  // ==================== RENDER ====================

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};

// ==================== HOOK ====================

export const useAuth = () => {
  const context = useContext(AuthContext);

  if (!context) {
    throw new Error(
      'useAuth deve ser usado dentro de AuthProvider'
    );
  }

  return context;
};
