import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
} from 'react';

import axios from 'axios';

const AuthContext = createContext(null);

const API_URL =
  process.env.REACT_APP_API_URL ||
  'https://sistema-dm.onrender.com/api';

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);

  const [loading, setLoading] = useState(true);

  // =========================
  // AXIOS
  // =========================

  const api = useMemo(() => {
    const instance = axios.create({
      baseURL: API_URL,
      withCredentials: true,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Interceptor de resposta
    instance.interceptors.response.use(
      (response) => response,
      async (error) => {
        if (error.response?.status === 401) {
          setUser(null);
        }

        return Promise.reject(error);
      }
    );

    return instance;
  }, []);

  // =========================
  // CARREGAR USUÁRIO
  // =========================

  const loadUser = async () => {
    try {
      setLoading(true);

      const response = await api.get('/auth/me');

      setUser(response.data);
    } catch (error) {
      setUser(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadUser();
  }, []);

  // =========================
  // LOGIN
  // =========================

  const login = async (email, password) => {
    try {
      const response = await api.post('/auth/login', {
        email,
        password,
      });

      setUser(response.data);

      return {
        success: true,
      };
    } catch (error) {
      return {
        success: false,
        message:
          error.response?.data?.detail ||
          'Erro ao fazer login',
      };
    }
  };

  // =========================
  // REGISTER
  // =========================

  const register = async (data) => {
    try {
      const response = await api.post(
        '/auth/register',
        data
      );

      setUser(response.data);

      return {
        success: true,
      };
    } catch (error) {
      return {
        success: false,
        message:
          error.response?.data?.detail ||
          'Erro ao registrar',
      };
    }
  };

  // =========================
  // LOGOUT
  // =========================

  const logout = async () => {
    try {
      await api.post('/auth/logout');
    } catch (error) {
      // ignora erro
    }

    setUser(null);
  };

  return (
    <AuthContext.Provider
      value={{
        api,
        user,
        loading,
        login,
        register,
        logout,
        loadUser,
        isAuthenticated: !!user,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);

  if (!context) {
    throw new Error(
      'useAuth deve ser usado dentro do AuthProvider'
    );
  }

  return context;
};
