import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { api, setAdminToken, getAdminToken } from '../api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [loading, setLoading] = useState(true);

  const checkAuth = useCallback(async () => {
    const token = getAdminToken();
    if (!token) {
      setIsAuthenticated(false);
      setLoading(false);
      return;
    }
    try {
      await api.checkAuth();
      setIsAuthenticated(true);
    } catch {
      setAdminToken('');
      setIsAuthenticated(false);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { checkAuth(); }, [checkAuth]);

  const login = async (password) => {
    const res = await api.login(password);
    setAdminToken(res.token);
    setIsAuthenticated(true);
  };

  const logout = async () => {
    try { await api.logout(); } catch {}
    setAdminToken('');
    setIsAuthenticated(false);
  };

  return (
    <AuthContext.Provider value={{ isAuthenticated, loading, login, logout, checkAuth }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
