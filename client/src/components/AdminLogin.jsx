import { useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { Shield, Lock, Eye, EyeOff, AlertCircle, Languages } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useLocale } from '../context/LocaleContext';

export default function AdminLogin() {
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const { isArabic, locale, toggleLocale } = useLocale();
  const navigate = useNavigate();

  const t = useMemo(() => ({
    title: isArabic ? 'دخول الإدارة' : 'Admin Access',
    subtitle: isArabic ? 'الرجاء إدخال كلمة المرور للمتابعة.' : 'Enter your password to continue.',
    passwordLabel: isArabic ? 'كلمة المرور' : 'Password',
    passwordPlaceholder: isArabic ? 'أدخل كلمة مرور الإدارة' : 'Enter admin password',
    login: isArabic ? 'الدخول إلى لوحة الإدارة' : 'Access Admin Panel',
    invalid: isArabic ? 'كلمة المرور غير صحيحة' : 'Invalid password',
    back: isArabic ? 'العودة إلى المحادثة' : 'Back to chat',
    locale: locale === 'ar' ? 'EN' : 'AR',
  }), [isArabic, locale]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await login(password);
      navigate('/admin');
    } catch (err) {
      setError(err.message || t.invalid);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen mne-soft-bg flex items-center justify-center relative overflow-hidden p-4">
      <div className="absolute inset-0 pointer-events-none">
        <div className="absolute top-[-260px] left-[5%] w-[520px] h-[520px] bg-[rgba(205,171,53,0.18)] rounded-full blur-[120px]" />
        <div className="absolute bottom-[-260px] right-[5%] w-[520px] h-[520px] bg-[rgba(35,40,45,0.12)] rounded-full blur-[120px]" />
      </div>

      <motion.div
        initial={{ opacity: 0, scale: 0.97 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.45 }}
        className="relative z-10 w-full max-w-md"
      >
        <div className="glass-card rounded-3xl p-7 sm:p-8">
          <div className={`flex items-center justify-between mb-6 ${isArabic ? 'flex-row-reverse' : ''}`}>
            <img src="/mne-logo.png" alt="MNE" className="w-36 h-auto" />
            <button onClick={toggleLocale} className="btn-ghost text-xs px-2.5 py-1.5 flex items-center gap-1">
              <Languages size={13} />
              {t.locale}
            </button>
          </div>

          <div className={`text-center mb-6 ${isArabic ? 'rtl:text-right' : ''}`}>
            <div className="inline-flex mb-4">
              <div className="w-14 h-14 rounded-2xl bg-[#23282d] flex items-center justify-center shadow-xl">
                <Shield size={28} className="text-white" />
              </div>
            </div>
            <h1 className="text-2xl font-extrabold text-gradient mb-1">{t.title}</h1>
            <p className="text-sm text-[#57616b]">{t.subtitle}</p>
          </div>

          <AnimatePresence>
            {error && (
              <motion.div
                initial={{ opacity: 0, y: -8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -8 }}
                className={`flex items-center gap-2.5 bg-red-500/10 border border-red-500/25 rounded-xl px-4 py-3 mb-5 ${isArabic ? 'flex-row-reverse text-right' : ''}`}
              >
                <AlertCircle size={16} className="text-red-600 flex-shrink-0" />
                <span className="text-sm text-red-700">{error}</span>
              </motion.div>
            )}
          </AnimatePresence>

          <form onSubmit={handleSubmit} className="space-y-5">
            <div className="space-y-2">
              <label className={`text-xs font-semibold text-[#6b737c] ${isArabic ? 'block text-right' : ''}`}>{t.passwordLabel}</label>
              <div className="relative">
                <Lock size={16} className={`absolute top-1/2 -translate-y-1/2 text-black/30 ${isArabic ? 'right-4' : 'left-4'}`} />
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder={t.passwordPlaceholder}
                  className={`w-full input-premium ${isArabic ? 'pr-11 pl-12 text-right' : 'pl-11 pr-12 text-left'}`}
                  autoFocus
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className={`absolute top-1/2 -translate-y-1/2 text-black/35 hover:text-black/60 transition-colors ${isArabic ? 'left-4' : 'right-4'}`}
                >
                  {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </div>

            <motion.button
              type="submit"
              disabled={loading || !password}
              whileHover={{ scale: 1.01 }}
              whileTap={{ scale: 0.985 }}
              className="btn-primary w-full flex items-center justify-center gap-2 text-base py-3.5 disabled:opacity-70"
            >
              {loading ? (
                <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              ) : t.login}
            </motion.button>
          </form>

          <div className={`mt-5 text-center ${isArabic ? 'rtl:text-right' : ''}`}>
            <a href="/" className="text-xs text-[#6d767e] hover:text-[#23282d] transition-colors">
              {isArabic ? '\u2190' : '\u2190'} {t.back}
            </a>
          </div>
        </div>
      </motion.div>
    </div>
  );
}

