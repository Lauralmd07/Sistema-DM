```javascript
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
    throw new Error('useAuth must be used within AuthProvider');
  }

  return context;
};

const api = axios.create({
  baseURL: 'https://sistema-dm.onrender.com/api',
  headers: {
    'Content-Type': 'application/json',
  },
});

export const AuthProvider = ({ children }) => {

  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {

    const token = localStorage.getItem('token');

    if (token) {
      api.defaults.headers.common[
        'Authorization'
      ] = `Bearer ${token}`;
    }

  }, []);

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

      const { data } = await api.post(
        '/auth/login',
        {
          email,
          password,
        }
      );

      if (data.token) {

        localStorage.setItem(
          'token',
          data.token
        );

        api.defaults.headers.common[
          'Authorization'
        ] = `Bearer ${data.token}`;
      }

      setUser(data.user || data);

      return {
        success: true
      };

    } catch (err) {

      console.error(err);

      return {
        success: false,
        error:
          err.response?.data?.detail ||
          err.message
      };
    }
  };

  const logout = async () => {

    localStorage.removeItem('token');

    delete api.defaults.headers.common[
      'Authorization'
    ];

    setUser(null);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        login,
        logout,
        api,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};
```
