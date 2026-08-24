import React, { useEffect, useRef, useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { Scale } from 'lucide-react';

export const Login = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const googleButtonRef = useRef(null);
  const { login, loginWithGoogle, user, loading: authLoading } = useAuth();
  const navigate = useNavigate();
  const googleClientId = process.env.REACT_APP_GOOGLE_CLIENT_ID || '';

  useEffect(() => {
    if (!authLoading && user) {
      navigate('/dashboard', { replace: true });
    }
  }, [authLoading, user, navigate]);

  useEffect(() => {
    if (authLoading || user || !googleClientId) return undefined;

    let attempts = 0;
    let timer;

    const renderGoogleButton = () => {
      if (!window.google?.accounts?.id || !googleButtonRef.current) {
        attempts += 1;
        if (attempts < 50) timer = window.setTimeout(renderGoogleButton, 100);
        return;
      }

      window.google.accounts.id.initialize({
        client_id: googleClientId,
        callback: async (response) => {
          setLoading(true);
          setError('');
          const result = await loginWithGoogle(response.credential);
          if (result.success) navigate('/dashboard', { replace: true });
          else setError(result.error);
          setLoading(false);
        },
      });

      googleButtonRef.current.innerHTML = '';
      window.google.accounts.id.renderButton(googleButtonRef.current, {
        type: 'standard',
        theme: 'outline',
        size: 'large',
        text: 'signin_with',
        shape: 'rectangular',
        width: 352,
        logo_alignment: 'left',
      });
    };

    if (!document.querySelector('script[data-google-gsi]')) {
      const script = document.createElement('script');
      script.src = 'https://accounts.google.com/gsi/client';
      script.async = true;
      script.defer = true;
      script.dataset.googleGsi = 'true';
      document.head.appendChild(script);
    }

    renderGoogleButton();
    return () => { if (timer) window.clearTimeout(timer); };
  }, [authLoading, user, googleClientId, loginWithGoogle, navigate]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    const result = await login(email, password);
    if (result.success) navigate('/dashboard', { replace: true });
    else setError(result.error);
    setLoading(false);
  };

  if (authLoading || user) {
    return <div className="min-h-screen bg-[#121212] flex items-center justify-center p-4"><div className="text-[#D4AF37] text-xl">Carregando...</div></div>;
  }

  return (
    <div className="min-h-screen bg-[#121212] flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-[#D4AF37] rounded-full mb-4"><Scale size={32} className="text-[#121212]" /></div>
          <h1 className="text-3xl font-bold text-[#D4AF37] mb-2">Sistema Jurídico</h1>
          <p className="text-[#F5F5F5]/60">Gestão profissional para advogados</p>
        </div>

        <div className="bg-[#1E1E1E] rounded-xl p-8 border border-[#3A3A3A] shadow-lg">
          <h2 className="text-2xl font-bold text-[#F5F5F5] mb-6">Login</h2>

          {error && <div className="mb-4 p-3 bg-red-900/20 border border-red-500/50 rounded-lg text-red-400 text-sm" data-testid="login-error">{error}</div>}

          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <label className="block text-sm font-medium text-[#F5F5F5] mb-2">Email</label>
              <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required data-testid="login-email-input" className="w-full px-4 py-3 bg-[#2A2A2A] border border-[#3A3A3A] rounded-lg text-[#F5F5F5] focus:outline-none focus:ring-2 focus:ring-[#D4AF37] transition-all" placeholder="seu@email.com" />
            </div>
            <div>
              <label className="block text-sm font-medium text-[#F5F5F5] mb-2">Senha</label>
              <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required data-testid="login-password-input" className="w-full px-4 py-3 bg-[#2A2A2A] border border-[#3A3A3A] rounded-lg text-[#F5F5F5] focus:outline-none focus:ring-2 focus:ring-[#D4AF37] transition-all" placeholder="••••••••" />
            </div>
            <button type="submit" disabled={loading} data-testid="login-submit-btn" className="w-full py-3 bg-[#D4AF37] hover:bg-[#E5C158] text-[#121212] font-bold rounded-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed">{loading ? 'Entrando...' : 'Entrar'}</button>
          </form>

          {googleClientId && (
            <>
              <div className="my-6 flex items-center gap-3"><div className="h-px flex-1 bg-[#3A3A3A]" /><span className="text-xs text-[#F5F5F5]/40">OU</span><div className="h-px flex-1 bg-[#3A3A3A]" /></div>
              <div ref={googleButtonRef} className="min-h-[40px] flex justify-center" aria-label="Entrar com Google" />
            </>
          )}

          <div className="mt-6 text-center">
            <p className="text-[#F5F5F5]/60 text-sm">Não tem uma conta? <Link to="/register" className="text-[#D4AF37] hover:text-[#E5C158] font-medium">Registre-se</Link></p>
          </div>
        </div>
      </div>
    </div>
  );
};
