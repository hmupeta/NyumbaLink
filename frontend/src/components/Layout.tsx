import { Link, Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'

export default function Layout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const handleLogout = async () => {
    await logout()
    navigate('/')
  }

  return (
    <div className="min-h-screen flex flex-col bg-gray-50">
      <header className="border-b bg-white shadow-sm">
        <div className="max-w-6xl mx-auto px-4 py-3 flex items-center justify-between">
          <Link to="/" className="text-xl font-bold text-emerald-700">
            NyumbaLink
          </Link>
          <nav className="flex items-center gap-4 text-sm">
            {user ? (
              <>
                <span className="text-gray-600 hidden sm:inline">{user.email}</span>
                {user.is_staff && (
                  <a
                    href="http://localhost:8000/admin/"
                    className="text-emerald-700 hover:underline"
                  >
                    Admin
                  </a>
                )}
                <button
                  onClick={handleLogout}
                  className="text-gray-700 hover:text-red-600"
                >
                  Logout
                </button>
              </>
            ) : (
              <>
                <Link to="/login" className="text-gray-700 hover:text-emerald-700">
                  Login
                </Link>
                <Link
                  to="/register"
                  className="bg-emerald-600 text-white px-3 py-1.5 rounded hover:bg-emerald-700"
                >
                  Register
                </Link>
              </>
            )}
          </nav>
        </div>
      </header>
      <main className="flex-1">
        <Outlet />
      </main>
      <footer className="border-t bg-white py-4 text-center text-sm text-gray-500">
        NyumbaLink · Find your place. Connect your world.
      </footer>
    </div>
  )
}
