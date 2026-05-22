import React, { useState } from 'react';

import {
  useNavigate,
  Link,
} from 'react-router-dom';

import { useAuth } from '../contexts/AuthContext';

import { Scale } from 'lucide-react';

export const Login = () => {
  const navigate = useNavigate();

  const { login } = useAuth();

  const [email, setEmail] = useState('');

  const [password, setPassword] = useState('');

  const [loading, setLoading] = useState(false);

  const [error, setError] = useState('');

  // =========================
  // SUBMIT
  // =========================

  const handleSubmit = async (e) => {
    e.preventDefault();

    setLoading(true);

    setError('');

    const result = await login(
      email,
      password
    );

    if (result.success) {
      navigate('/dashboard');
    } else {
      setError(result.message);
    }

    setLoading(false);
  };

  return (
    <div className="min-h-screen bg-[#121212] flex items-center justify-center p-4">

      <div className="w-full max-w-md">

        {/* LOGO */}

        <div className="text-center mb-8">

          <div className="inline-flex items-center justify-center w-16 h-16 bg-[#D4AF37] rounded-full mb-4">
            <Scale
              size={32}
              className="text-[#121212]"
            />
          </div>

          <h1 className="text-3xl font-bold text-[#D4AF37] mb-2">
            Sistema Jurídico
          </h1>

          <p className="text-[#F5F5F5]/60">
            Gestão profissional para advogados
          </p>

        </div>

        {/* CARD */}

        <div className="bg-[#1E1E1E] rounded-xl p-8 border border-[#3A3A3A] shadow-lg">

          <h2 className="text-2xl font-bold text-[#F5F5F5] mb-6">
            Login
          </h2>

          {/* ERROR */}

          {error && (
            <div
              data-testid="login-error"
              className="mb-4 p-3 bg-red-900/20 border border-red-500/50 rounded-lg text-red-400 text-sm"
            >
              {error}
            </div>
          )}

          {/* FORM */}

          <form
            onSubmit={handleSubmit}
            className="space-y-6"
          >

            {/* EMAIL */}

            <div>

              <label className="block text-sm font-medium text-[#F5F5F5] mb-2">
                Email
              </label>

              <input
                type="email"
                required
                value={email}
                onChange={(e) =>
                  setEmail(e.target.value)
                }
                placeholder="seu@email.com"
                data-testid="login-email-input"
                autoComplete="email"
                className="w-full px-4 py-3 bg-[#2A2A2A] border border-[#3A3A3A] rounded-lg text-[#F5F5F5] focus:outline-none focus:ring-2 focus:ring-[#D4AF37] transition-all"
              />

            </div>

            {/* PASSWORD */}

            <div>

              <label className="block text-sm font-medium text-[#F5F5F5] mb-2">
                Senha
              </label>

              <input
                type="password"
                required
                value={password}
                onChange={(e) =>
                  setPassword(e.target.value)
                }
                placeholder="••••••••"
                data-testid="login-password-input"
                autoComplete="current-password"
                className="w-full px-4 py-3 bg-[#2A2A2A] border border-[#3A3A3A] rounded-lg text-[#F5F5F5] focus:outline-none focus:ring-2 focus:ring-[#D4AF37] transition-all"
              />

            </div>

            {/* BUTTON */}

            <button
              type="submit"
              disabled={loading}
              data-testid="login-submit-btn"
              className="w-full py-3 bg-[#D4AF37] hover:bg-[#E5C158] text-[#121212] font-bold rounded-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading
                ? 'Entrando...'
                : 'Entrar'}
            </button>

          </form>

          {/* FOOTER */}

          <div className="mt-6 text-center">

            <p className="text-[#F5F5F5]/60 text-sm">

              Não tem uma conta?{' '}

              <Link
                to="/register"
                className="text-[#D4AF37] hover:text-[#E5C158] font-medium"
              >
                Registre-se
              </Link>

            </p>

          </div>

        </div>

      </div>

    </div>
  );
};
