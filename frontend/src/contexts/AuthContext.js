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

const api = axios.create({
  baseURL: process.env.REACT_APP_API_URL || 'https://sistema-dm.onrender.com/api',
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const AuthProvider = ({ children }) => {

  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const checkAuth = useCallback(async () => {
    try {
      const { data } = await api.get('/auth/me');
      setUser(data);
    } catch (err) {
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  const login = async (email, password) => {
    try {
      setError(null);

      const { data } = await api.post(
        '/auth/login',
        {
          email,
          password,
        }
      );

      setUser(data);

      return {
        success: true
      };

    } catch (err) {
      console.error(err);

      const errorMsg =
        err.response?.data?.detail ||
        'Erro ao fazer login';

      setError(errorMsg);

      return {
        success: false,
        error: errorMsg
      };
    }
  };

  const loginWithGoogle = async (credential) => {
    try {
      setError(null);

      const { data } = await api.post(
        '/auth/google',
        { credential }
      );

      setUser(data);

      return {
        success: true,
        user: data
      };

    } catch (err) {
      console.error(err);

      const errorMsg =
        err.response?.data?.detail ||
        'Erro ao entrar com Google';

      setError(errorMsg);

      return {
        success: false,
        error: errorMsg
      };
    }
  };

  const register = async (
    name,
    email,
    password,
    role = 'lawyer'
  ) => {
    try {
      setError(null);

      const { data } = await api.post(
        '/auth/register',
        {
          name,
          email,
          password,
          role,
        }
      );

      setUser(data);

      return {
        success: true
      };

    } catch (err) {
      console.error(err);

      const errorMsg =
        err.response?.data?.detail ||
        'Erro ao registrar';

      setError(errorMsg);

      return {
        success: false,
        error: errorMsg
      };
    }
  };

  const logout = async () => {
    try {
      await api.post('/auth/logout');
    } catch (err) {
      console.error(err);
    } finally {
      setUser(null);
    }
  };

  const value = {
    user,
    loading,
    error,
    login,
    loginWithGoogle,
    register,
    logout,
    api,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};

export default AuthContext;
