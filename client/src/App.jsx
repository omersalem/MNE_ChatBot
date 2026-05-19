import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from './context/AuthContext';
import Layout from './components/Layout';
import Chat from './pages/Chat';
import Admin from './pages/Admin';
import AdminLogin from './components/AdminLogin';
import { AnimatePresence } from 'framer-motion';

function ProtectedRoute({ children }) {
  const { isAuthenticated, loading } = useAuth();
  if (loading) return <div className="flex items-center justify-center h-screen mne-soft-bg"><div className="w-8 h-8 border-2 border-[#cdab35]/40 border-t-[#cdab35] rounded-full animate-spin" /></div>;
  if (!isAuthenticated) return <Navigate to="/admin/login" replace />;
  return children;
}

export default function App() {
  return (
    <AnimatePresence mode="wait">
      <Routes>
        <Route path="/admin/login" element={<AdminLogin />} />
        <Route path="/admin" element={
          <ProtectedRoute>
            <Layout><Admin /></Layout>
          </ProtectedRoute>
        } />
        <Route path="*" element={<Layout><Chat /></Layout>} />
      </Routes>
    </AnimatePresence>
  );
}
