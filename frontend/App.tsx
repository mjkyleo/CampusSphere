import React, { Suspense, lazy } from 'react';
import { BrowserRouter, Routes, Route, useLocation } from 'react-router-dom';
import { ToastProvider } from './context/ToastContext.tsx';
import { AuthProvider, useAuth } from './context/AuthContext.tsx';
import { Navbar } from './components/Navbar.tsx';
import { ReportModal } from './components/ReportModal.tsx';
import { NotFound } from './components/NotFound.tsx';
import { ErrorBoundary } from './components/ErrorBoundary.tsx';
import { ProtectedRoute } from './components/ProtectedRoute.tsx';
import { AdminRoute } from './components/AdminRoute.tsx';
import { PublicOnlyRoute } from './components/PublicOnlyRoute.tsx';

// Pages — 路由级懒加载（按需 split chunk，recharts 等重依赖随各自页面懒加载）
const HomePage = lazy(() => import('./pages/HomePage.tsx'));
const MarketList = lazy(() => import('./pages/MarketList.tsx'));
const MarketDetail = lazy(() => import('./pages/MarketDetail.tsx'));
const MarketPublish = lazy(() => import('./pages/MarketPublish.tsx'));
const CourseSearch = lazy(() => import('./pages/CourseSearch.tsx'));
const CourseDetail = lazy(() => import('./pages/CourseDetail.tsx'));
const CourseReview = lazy(() => import('./pages/CourseReview.tsx'));
const CanteenList = lazy(() => import('./pages/CanteenList.tsx'));
const CanteenStall = lazy(() => import('./pages/CanteenStall.tsx'));
const TeammatePost = lazy(() => import('./pages/TeammatePost.tsx'));
const ShareFeed = lazy(() => import('./pages/ShareFeed.tsx'));
const JobList = lazy(() => import('./pages/JobList.tsx'));
const { TeamDetail, ShareDetail, JobDetail } = {
  TeamDetail: lazy(() => import('./pages/ModuleDetail.tsx').then((m) => ({ default: m.TeamDetail }))),
  ShareDetail: lazy(() => import('./pages/ModuleDetail.tsx').then((m) => ({ default: m.ShareDetail }))),
  JobDetail: lazy(() => import('./pages/ModuleDetail.tsx').then((m) => ({ default: m.JobDetail }))),
};
const MessageCenter = lazy(() => import('./pages/MessageCenter.tsx'));
const UserProfile = lazy(() => import('./pages/UserProfile.tsx'));
const AdminDashboard = lazy(() => import('./pages/AdminDashboard.tsx'));
const AdminLoginPage = lazy(() => import('./pages/AdminLoginPage.tsx'));
const LoginPage = lazy(() => import('./pages/LoginPage.tsx'));

const PageFallback: React.FC = () => (
  <div className="min-h-[50vh] flex items-center justify-center">
    <div className="text-center space-y-3">
      <div className="w-10 h-10 border-4 border-ink border-t-transparent rounded-full animate-spin mx-auto"></div>
      <p className="mono-label text-slate">正在加载...</p>
    </div>
  </div>
);

const AppContent: React.FC = () => {
  const { loading, adminLoading } = useAuth();
  const location = useLocation();
  const isLoginPage = location.pathname === '/login';
  const isAdminLogin = location.pathname === '/admin/login';

  if (loading || adminLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-ground">
        <div className="text-center space-y-3">
          <div className="w-12 h-12 border-4 border-ink border-t-transparent rounded-full animate-spin mx-auto"></div>
          <p className="mono-label text-slate">正在进入 CampusSphere 校园平台...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-ground text-ink pb-20 lg:pb-12 lg:pt-16 antialiased selection:bg-ink selection:text-surface">
      {!isLoginPage && !isAdminLogin && <Navbar />}
      <main className={isLoginPage || isAdminLogin ? '' : 'max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6'}>
        <Suspense fallback={<PageFallback />}>
          <ErrorBoundary>
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
              <Route path="/teammates/:id" element={<TeamDetail />} />
              <Route path="/share" element={<ShareFeed />} />
              <Route path="/share/:id" element={<ShareDetail />} />
              <Route path="/jobs" element={<JobList />} />
              <Route path="/jobs/:id" element={<JobDetail />} />
              <Route path="/messages" element={<ProtectedRoute><MessageCenter /></ProtectedRoute>} />
              <Route path="/profile" element={<ProtectedRoute><UserProfile /></ProtectedRoute>} />
              <Route path="/admin" element={<AdminRoute><AdminDashboard /></AdminRoute>} />
              <Route path="/admin/login" element={<AdminLoginPage />} />
              <Route path="/login" element={<PublicOnlyRoute><LoginPage /></PublicOnlyRoute>} />
              <Route path="*" element={<NotFound />} />
            </Routes>
          </ErrorBoundary>
        </Suspense>
      </main>
      {!isLoginPage && !isAdminLogin && <ReportModal />}
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
