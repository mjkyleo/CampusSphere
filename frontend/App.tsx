import React from 'react';
import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { ToastProvider } from './context/ToastContext.tsx';
import { AuthProvider, useAuth } from './context/AuthContext.tsx';
import { Navbar } from './components/Navbar.tsx';
import { ReportModal } from './components/ReportModal.tsx';
import { ProtectedRoute } from './components/ProtectedRoute.tsx';
import { AdminRoute } from './components/AdminRoute.tsx';
import { PublicOnlyRoute } from './components/PublicOnlyRoute.tsx';

// Pages
import HomePage from './pages/HomePage.tsx';
import MarketList from './pages/MarketList.tsx';
import MarketDetail from './pages/MarketDetail.tsx';
import MarketPublish from './pages/MarketPublish.tsx';
import CourseSearch from './pages/CourseSearch.tsx';
import CourseDetail from './pages/CourseDetail.tsx';
import CourseReview from './pages/CourseReview.tsx';
import CanteenList from './pages/CanteenList.tsx';
import CanteenStall from './pages/CanteenStall.tsx';
import TeammatePost from './pages/TeammatePost.tsx';
import ShareFeed from './pages/ShareFeed.tsx';
import JobList from './pages/JobList.tsx';
import MessageCenter from './pages/MessageCenter.tsx';
import UserProfile from './pages/UserProfile.tsx';
import AdminDashboard from './pages/AdminDashboard.tsx';
import LoginPage from './pages/LoginPage.tsx';

const AppContent: React.FC = () => {
  const { loading, adminLoading } = useAuth();
  const location = useLocation();
  const isLoginPage = location.pathname === '/login';

  if (loading || adminLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <div className="text-center space-y-3">
          <div className="w-12 h-12 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin mx-auto"></div>
          <p className="text-sm font-bold text-slate-600">正在进入 CampusSphere 校园平台...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50/60 text-slate-800 pb-20 lg:pb-12 lg:pt-16 antialiased selection:bg-indigo-500 selection:text-white">
      {!isLoginPage && <Navbar />}
      <main className={isLoginPage ? '' : 'max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6'}>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/market" element={<MarketList />} />
          <Route path="/market/:id" element={<MarketDetail />} />
          <Route path="/market/publish" element={<ProtectedRoute><MarketPublish /></ProtectedRoute>} />
          <Route path="/courses" element={<CourseSearch />} />
          <Route path="/courses/:id" element={<CourseDetail />} />
          <Route path="/courses/review" element={<ProtectedRoute><CourseReview /></ProtectedRoute>} />
          <Route path="/courses/:id/review" element={<ProtectedRoute><CourseReview /></ProtectedRoute>} />
          <Route path="/canteens" element={<CanteenList />} />
          <Route path="/canteens/:id" element={<CanteenStall />} />
          <Route path="/canteens/stall/:id" element={<CanteenStall />} />
          <Route path="/teammates" element={<TeammatePost />} />
          <Route path="/share" element={<ShareFeed />} />
          <Route path="/jobs" element={<JobList />} />
          <Route path="/messages" element={<ProtectedRoute><MessageCenter /></ProtectedRoute>} />
          <Route path="/profile" element={<ProtectedRoute><UserProfile /></ProtectedRoute>} />
          <Route path="/admin" element={<AdminRoute><AdminDashboard /></AdminRoute>} />
          <Route path="/login" element={<PublicOnlyRoute><LoginPage /></PublicOnlyRoute>} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
      {!isLoginPage && <ReportModal />}
    </div>
  );
};

const App: React.FC = () => {
  return (
    <ToastProvider>
      <AuthProvider>
        <BrowserRouter>
          <AppContent />
        </BrowserRouter>
      </AuthProvider>
    </ToastProvider>
  );
};

export default App;
