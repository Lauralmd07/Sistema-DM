import React, {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback
} from 'react';

import axios from 'axios';

const AuthContext = createContext(null);

export const useAuth = () => {
  const context = useContext(AuthContext);

  if (!context) {
    throw new Error(
      'useAuth must be used within AuthProvider'
    );
  }

  return context;
};

// ==================== API ====================

export const api = axios.create({
  baseURL: 'https://sistema-dm.onrender.com/api',
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
  },
});

// ==================== ERROR FORMAT ====================

function formatApiErrorDetail(detail) {
  if (!detail) {
    return 'Algo deu errado. Tente novamente.';
  }

  if (typeof detail === 'string') {
    return detail;
  }

  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        if (item?.msg) return item.msg;
        return JSON.stringify(item);
      })
      .join(' ');
  }

  if (detail?.msg) {
    return detail.msg;
  }

  return String(detail);
}

// ==================== PROVIDER ====================

export const AuthProvider = ({ children }) => {

  const [user, setUser] = useState(null);

  const [loading, setLoading] = useState(true);

  const [error, setError] = useState(null);

  // ==================== CHECK AUTH ====================

  const checkAuth = useCallback(async () => {

    try {

      setLoading(true);

      const response = await api.get('/auth/me');

      setUser(response.data);

    } catch (err) {

      console.error(
        'Auth check error:',
        err.response?.data || err.message
      );

      setUser(null);

    } finally {

      setLoading(false);

    }

  }, []);

  // ==================== INITIAL LOAD ====================

  useEffect(() => {

    checkAuth();

  }, [checkAuth]);

  // ==================== LOGIN ====================

  const login = async (email, password) => {

    try {

      setError(null);

      const response = await api.post(
        '/auth/login',
        {
          email,
          password,
        }
      );

      setUser(response.data);

      return {
        success: true,
      };

    } catch (err) {

      console.error(
        'Login error:',
        err.response?.data || err.message
      );

      const errorMsg =
        formatApiErrorDetail(
          err.response?.data?.detail
        ) || 'Erro ao fazer login';

      setError(errorMsg);

      return {
        success: false,
        error: errorMsg,
      };
    }
  };

  // ==================== REGISTER ====================

  const register = async (
    name,
    email,
    password,
    role = 'lawyer'
  ) => {

    try {

      setError(null);

      const response = await api.post(
        '/auth/register',
        {
          name,
          email,
          password,
          role,
        }
      );

      setUser(response.data);

      return {
        success: true,
      };

    } catch (err) {

      console.error(
        'Register error:',
        err.response?.data || err.message
      );

      const errorMsg =
        formatApiErrorDetail(
          err.response?.data?.detail
        ) || 'Erro ao registrar';

      setError(errorMsg);

      return {
        success: false,
        error: errorMsg,
      };
    }
  };

  // ==================== LOGOUT ====================

  const logout = async () => {

    try {

      await api.post('/auth/logout');

    } catch (err) {

      console.error(
        'Logout error:',
        err.response?.data || err.message
      );

    } finally {

      setUser(null);

    }
  };

  // ==================== CONTEXT VALUE ====================

  const value = {
    user,
    loading,
    error,
    login,
    register,
    logout,
    checkAuth,
    api,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};
