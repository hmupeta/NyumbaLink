import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import HomePage from './pages/HomePage'
import LoginPage from './pages/LoginPage'
import ForgotPasswordPage from './pages/ForgotPasswordPage'
import ResetPasswordPage from './pages/ResetPasswordPage'
import RegisterPage from './pages/RegisterPage'
import ListingDetailPage from './pages/ListingDetailPage'
import NotFoundPage from './pages/NotFoundPage'
import DashboardPage from './pages/DashboardPage'
import CreateListingPage from './pages/CreateListingPage'
import ManageListingPage from './pages/ManageListingPage'
import EditListingPage from './pages/EditListingPage'
import VerificationPage from './pages/VerificationPage'
import WalletPage from './pages/WalletPage'
import PaymentSettingsPage from './pages/PaymentSettingsPage'
import InboxPage from './pages/InboxPage'
import SavedPropertiesPage from './pages/SavedPropertiesPage'
import PublicProfilePage from './pages/PublicProfilePage'
import LeaseAgreementPage from './pages/LeaseAgreementPage'
import ModerationPage from './pages/ModerationPage'
import AdminDashboard from './pages/AdminDashboard'
import ProtectedRoute from './auth/ProtectedRoute'

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<HomePage />} />
        <Route path="/listings/:id" element={<ListingDetailPage />} />
        <Route path="/profiles/:id" element={<PublicProfilePage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/forgot-password" element={<ForgotPasswordPage />} />
        <Route path="/reset-password/:uid/:token" element={<ResetPasswordPage />} />
        <Route path="/register" element={<RegisterPage />} />
        
        <Route element={<ProtectedRoute />}>
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/dashboard/listings/new" element={<CreateListingPage />} />
          <Route path="/dashboard/listings/:id" element={<ManageListingPage />} />
          <Route path="/dashboard/listings/:id/edit" element={<EditListingPage />} />
          <Route path="/verification" element={<VerificationPage />} />
          <Route path="/wallet" element={<WalletPage />} />
          <Route path="/settings" element={<PaymentSettingsPage />} />
          <Route path="/leases/:id" element={<LeaseAgreementPage />} />
          <Route path="/moderation" element={<ModerationPage />} />
          <Route path="/admin-dashboard" element={<AdminDashboard />} />
          <Route path="/inbox" element={<InboxPage />} />
          <Route path="/saved" element={<SavedPropertiesPage />} />
        </Route>
        
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  )
}
