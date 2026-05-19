import { useMemo, useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { MessageSquare, Shield, LogOut, Menu, ChevronLeft, Languages, CheckCircle2 } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useLocale } from '../context/LocaleContext';

const sidebarVariants = {
  open: { width: 292, transition: { duration: 0.3, ease: [0.25, 0.1, 0.25, 1] } },
  closed: { width: 84, transition: { duration: 0.3, ease: [0.25, 0.1, 0.25, 1] } },
};

export default function Layout({ children }) {
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [toast, setToast] = useState(null);
  const [loggingOut, setLoggingOut] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  const { logout } = useAuth();
  const { isArabic, locale, toggleLocale } = useLocale();

  const text = useMemo(() => ({
    navChat: isArabic ? 'المحادثة' : 'Chat',
    navAdmin: isArabic ? 'لوحة الإدارة' : 'Admin',
    logout: isArabic ? 'تسجيل الخروج' : 'Logout',
    logoutSuccess: isArabic ? 'تم تسجيل الخروج بنجاح.' : 'Logged out successfully.',
    language: locale === 'ar' ? 'EN' : 'AR',
    subtitle: isArabic ? 'منصة المساعد الذكي' : 'AI Assistant Platform',
  }), [isArabic, locale]);

  const navTop = [
    { icon: MessageSquare, label: text.navChat, path: '/' },
  ];

  const navBottom = [
    { icon: Shield, label: text.navAdmin, path: '/admin' },
  ];

  const showToast = (msg) => {
    setToast({ msg });
    setTimeout(() => setToast(null), 1800);
  };

  const handleLogout = async () => {
    if (loggingOut) return;
    setLoggingOut(true);
    showToast(text.logoutSuccess);
    setTimeout(async () => {
      try {
        await logout();
        navigate('/', { replace: true });
      } finally {
        setLoggingOut(false);
      }
    }, 420);
  };

  const NavItem = ({ icon: Icon, label, path, onClick }) => {
    const isActive = location.pathname === path;
    return (
      <motion.button
        type="button"
        whileHover={{ x: isArabic ? -3 : 3 }}
        whileTap={{ scale: 0.985 }}
        onClick={() => { navigate(path); onClick?.(); }}
        className={`relative flex items-center gap-3 w-full px-4 py-3 rounded-xl transition-all duration-300
          ${collapsed ? 'justify-center' : ''}
          ${isActive
            ? 'text-[#171a1f] bg-[rgba(205,171,53,0.22)] border border-[rgba(205,171,53,0.5)]'
            : 'text-[#40464d] hover:text-[#1e2328] hover:bg-[rgba(205,171,53,0.12)] border border-transparent'
          }`}
      >
        {isActive && (
          <motion.div
            layoutId="nav-active-mne"
            className={`absolute inset-y-2 ${isArabic ? 'right-0' : 'left-0'} w-1 rounded-full bg-[#cdab35]`}
            transition={{ type: 'spring', stiffness: 330, damping: 28 }}
          />
        )}
        <Icon size={19} className="relative z-10 flex-shrink-0" />
        {!collapsed && <span className="text-sm font-semibold whitespace-nowrap">{label}</span>}
      </motion.button>
    );
  };

  const sidebarContent = (
    <div className={`flex flex-col h-full ${collapsed ? 'items-center' : ''}`}>
      <div className={`px-4 py-5 border-b border-black/10 ${collapsed ? 'space-y-2' : ''}`}>
        <div className={`flex ${collapsed ? 'flex-col items-center' : 'items-start'} gap-3`}>
          <img src="/mne-logo.png" alt="MNE" className={`${collapsed ? 'w-14' : 'w-44'} h-auto`} />
          {!collapsed && (
            <motion.div initial={{ opacity: 0, y: 3 }} animate={{ opacity: 1, y: 0 }} className="leading-tight">
              <div className="text-xs text-[#876f1f]">{text.subtitle}</div>
            </motion.div>
          )}
        </div>
        <div className={`flex items-center ${collapsed ? 'justify-center mt-2' : 'justify-between mt-4'}`}>
          {!collapsed && (
            <button type="button" onClick={toggleLocale} className={`btn-ghost text-xs px-3 py-1.5 flex items-center gap-1.5 ${isArabic ? 'flex-row-reverse' : ''}`}>
              <Languages size={14} />
              {text.language}
            </button>
          )}
          <button
            type="button"
            onClick={() => setCollapsed(!collapsed)}
            className="hidden lg:flex text-[#5f6770] hover:text-[#23282d] transition-colors"
          >
            <ChevronLeft size={16} className={`transition-transform ${collapsed ? 'rotate-180' : ''} ${isArabic ? 'rotate-180' : ''}`} />
          </button>
        </div>
      </div>

      <div className="flex-1 px-3 py-4 space-y-1 overflow-y-auto no-scrollbar">
        {navTop.map((item) => (<NavItem key={item.path} {...item} />))}
      </div>

      <div className="px-4 py-2">
        <div className="h-px bg-gradient-to-r from-transparent via-[#cdab35]/45 to-transparent" />
      </div>

      <div className="px-3 pb-4 space-y-1">
        {navBottom.map((item) => (<NavItem key={item.path} {...item} />))}
        <motion.button
          type="button"
          whileHover={{ x: isArabic ? -3 : 3 }}
          whileTap={{ scale: 0.985 }}
          onClick={handleLogout}
          disabled={loggingOut}
          className={`flex items-center gap-3 w-full px-4 py-3 rounded-xl text-[#6a7178] hover:text-[#9e1f1f] hover:bg-[rgba(190,20,20,0.08)] transition-all duration-300 ${collapsed ? 'justify-center' : ''}`}
        >
          <LogOut size={19} />
          {!collapsed && <span className="text-sm font-semibold">{text.logout}</span>}
        </motion.button>
      </div>
    </div>
  );

  return (
    <div className="mne-app-shell flex h-screen overflow-hidden">
      <motion.aside
        variants={sidebarVariants}
        animate={collapsed ? 'closed' : 'open'}
        className={`hidden lg:flex relative z-30 h-full glass overflow-hidden ${isArabic ? 'border-l border-black/10' : 'border-r border-black/10'}`}
      >
        {sidebarContent}
      </motion.aside>

      <AnimatePresence>
        {mobileOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setMobileOpen(false)}
            className="fixed inset-0 z-40 bg-black/45 backdrop-blur-[2px] lg:hidden"
          />
        )}
      </AnimatePresence>

      <AnimatePresence>
        {mobileOpen && (
          <motion.aside
            initial={{ x: isArabic ? 300 : -300 }}
            animate={{ x: 0, transition: { type: 'spring', damping: 24, stiffness: 230 } }}
            exit={{ x: isArabic ? 300 : -300 }}
            className={`fixed ${isArabic ? 'right-0' : 'left-0'} top-0 bottom-0 z-50 w-72 glass lg:hidden ${isArabic ? 'border-l border-black/10' : 'border-r border-black/10'}`}
          >
            {sidebarContent}
          </motion.aside>
        )}
      </AnimatePresence>

      <div className="flex-1 flex flex-col min-w-0 relative">
        <div className="lg:hidden flex items-center justify-between px-4 py-3 glass border-b border-black/10">
          <button type="button" onClick={() => setMobileOpen(true)} className="text-[#5a6169] hover:text-[#23282d]">
            <Menu size={23} />
          </button>
          <img src="/mne-logo.png" alt="MNE" className="w-28 h-auto" />
          <button type="button" onClick={toggleLocale} className="btn-ghost text-xs px-2.5 py-1.5">{text.language}</button>
        </div>

        <div className="flex-1 overflow-hidden relative">
          {children}
        </div>
      </div>

      <AnimatePresence>
        {toast && (
          <motion.div
            initial={{ opacity: 0, y: 14 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 14 }}
            className={`fixed bottom-5 ${isArabic ? 'left-5' : 'right-5'} z-[70] px-4 py-2.5 rounded-xl shadow-xl bg-[#f2fbf4] border border-[#5aa56a]/45 text-[#1f4d2a] flex items-center gap-2 ${isArabic ? 'flex-row-reverse' : ''}`}
          >
            <CheckCircle2 size={16} className="text-[#2d7a40]" />
            <span className="text-sm font-medium">{toast.msg}</span>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
