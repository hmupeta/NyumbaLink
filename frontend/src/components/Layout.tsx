import { Link, Outlet, useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import NotificationBell from './NotificationBell'

export default function Layout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()

  const isActive = (path: string) => location.pathname === path ? 'text-emerald-700 font-bold' : 'text-gray-700 hover:text-emerald-700'

  return (
    <div className="min-h-screen flex flex-col bg-gray-50 font-sans">
      
      <header className="border-b bg-white shadow-sm sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-4 py-3 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2">
  <img src="/logo.png" alt="NyumbaLink" className="h-20 w-auto object-contain" />
  <span className="text-xl font-bold text-emerald-700 tracking-tight">NyumbaLink</span>
</Link>
          <nav className="flex items-center gap-6 text-sm">
            {user ? (
              <>
                <Link to="/dashboard" className={isActive('/dashboard')}>Dashboard</Link>
                <Link to="/saved" className={isActive('/saved')}>Saved</Link>
                <Link to="/inbox" className={isActive('/inbox')}>Inbox</Link>
                <Link to="/wallet" className={isActive('/wallet')}>Wallet</Link>
                {user.is_staff && <Link to="/admin-dashboard" className="text-purple-700 font-bold hover:text-purple-800">Admin Overview</Link>}
                {user.is_staff && <Link to="/moderation" className="text-orange-600 font-bold hover:text-orange-700">Moderation</Link>}
                <NotificationBell />
                <span className="text-gray-300">|</span>
                <span className="text-gray-600 hidden sm:inline font-medium">{user.email}</span>
                <button onClick={() => { logout(); navigate('/') }} className="text-red-600 hover:underline font-medium">Logout</button>
              </>
            ) : (
              <>
                <Link to="/login" className="text-gray-700 hover:text-emerald-700 font-medium">Login</Link>
                <Link to="/register" className="bg-emerald-600 text-white px-4 py-1.5 rounded-md hover:bg-emerald-700 font-medium transition">Register</Link>
              </>
            )}
          </nav>
        </div>
      </header>

      <main className="flex-1"><Outlet /></main>

      <footer className="bg-slate-900 text-slate-300 pt-16 pb-8 border-t border-slate-800 mt-auto">
        <div className="max-w-6xl mx-auto px-4">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-12 mb-12">
            <div>
              <Link to="/" className="text-2xl font-bold text-white tracking-tight block mb-4">NyumbaLink</Link>
              <p className="text-sm text-slate-400 mb-6 leading-relaxed">Find your place. Connect your world. The most trusted property marketplace in Zambia.</p>
            </div>
            <div>
              <h4 className="text-white font-semibold mb-4 text-sm uppercase tracking-wider">Explore</h4>
              <ul className="space-y-3 text-sm">
                <li><Link to="/?type=rent" className="hover:text-emerald-400 transition">Rent a Home</Link></li>
                <li><Link to="/?type=sale" className="hover:text-emerald-400 transition">Buy a Home</Link></li>
                <li><Link to="/" className="hover:text-emerald-400 transition">All Listings</Link></li>
              </ul>
            </div>
            <div>
              <h4 className="text-white font-semibold mb-4 text-sm uppercase tracking-wider">For Landlords</h4>
              <ul className="space-y-3 text-sm">
                <li><Link to="/dashboard/listings/new" className="hover:text-emerald-400 transition">List a Property</Link></li>
                <li><Link to="/verification" className="hover:text-emerald-400 transition">Get Verified</Link></li>
                <li><Link to="/wallet" className="hover:text-emerald-400 transition">Pricing & Plans</Link></li>
              </ul>
            </div>
            <div>
              <h4 className="text-white font-semibold mb-4 text-sm uppercase tracking-wider">Support</h4>
              <ul className="space-y-3 text-sm mb-6">
                <li><a href="#" className="hover:text-emerald-400 transition">Help Centre</a></li>
                <li><a href="#" className="hover:text-emerald-400 transition">Contact Us</a></li>
              </ul>
            </div>
          </div>
          <div className="border-t border-slate-800 pt-8 flex flex-col md:flex-row justify-between items-center gap-4 text-xs text-slate-500">
            <div className="flex gap-4">
              <a href="#" className="hover:text-white transition">Terms of Use</a>
              <a href="#" className="hover:text-white transition">Privacy Policy</a>
            </div>
            <p>© {new Date().getFullYear()} NyumbaLink. All rights reserved.</p>
          </div>
        </div>
      </footer>
    </div>
  )
}
