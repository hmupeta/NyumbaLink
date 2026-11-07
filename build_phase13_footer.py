#!/usr/bin/env python3
"""NyumbaLink Phase 13: Rich Footer."""
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path.cwd()
FRONTEND = ROOT / "frontend"
LAYOUT_FILE = FRONTEND / "src" / "components" / "Layout.tsx"

# We rewrite Layout.tsx to include the new Footer and keep the Header navigation
LAYOUT_CONTENT = '''
import { Link, Outlet, useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'

export default function Layout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()

  const isActive = (path: string) => location.pathname === path ? 'text-emerald-700 font-bold' : 'text-gray-700 hover:text-emerald-700'

  return (
    <div className="min-h-screen flex flex-col bg-gray-50 font-sans">
      
      {/* HEADER */}
      <header className="border-b bg-white shadow-sm sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-4 py-3 flex items-center justify-between">
          <Link to="/" className="text-xl font-bold text-emerald-700 tracking-tight">NyumbaLink</Link>
          <nav className="flex items-center gap-6 text-sm">
            {user ? (
              <>
                <Link to="/dashboard" className={isActive('/dashboard')}>Dashboard</Link>
                <Link to="/saved" className={isActive('/saved')}>Saved</Link>
                <Link to="/inbox" className={isActive('/inbox')}>Inbox</Link>
                <Link to="/wallet" className={isActive('/wallet')}>Wallet</Link>
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

      {/* MAIN CONTENT */}
      <main className="flex-1"><Outlet /></main>

      {/* RICH FOOTER */}
      <footer className="bg-slate-900 text-slate-300 pt-16 pb-8 border-t border-slate-800 mt-auto">
        <div className="max-w-6xl mx-auto px-4">
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-12 mb-12">
            
            {/* Brand & Social */}
            <div>
              <Link to="/" className="text-2xl font-bold text-white tracking-tight block mb-4">NyumbaLink</Link>
              <p className="text-sm text-slate-400 mb-6 leading-relaxed">
                Find your place. Connect your world. The most trusted property marketplace in Zambia.
              </p>
              <div className="flex gap-4">
                {/* Facebook */}
                <a href="#" className="text-slate-400 hover:text-white transition"><svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor"><path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.469h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.469h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z"/></svg></a>
                {/* Twitter / X */}
                <a href="#" className="text-slate-400 hover:text-white transition"><svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor"><path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/></svg></a>
                {/* Instagram */}
                <a href="#" className="text-slate-400 hover:text-white transition"><svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zM12 0C8.741 0 8.333.014 7.053.072 2.695.272.273 2.69.073 7.052.014 8.333 0 8.741 0 12c0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98C8.333 23.986 8.741 24 12 24c3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98C15.668.014 15.259 0 12 0zm0 5.838a6.162 6.162 0 100 12.324 6.162 6.162 0 000-12.324zM12 16a4 4 0 110-8 4 4 0 010 8zm6.406-11.845a1.44 1.44 0 100 2.881 1.44 1.44 0 000-2.881z"/></svg></a>
                {/* LinkedIn */}
                <a href="#" className="text-slate-400 hover:text-white transition"><svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor"><path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433c-1.144 0-2.063-.926-2.063-2.065 0-1.138.92-2.063 2.063-2.063 1.14 0 2.064.925 2.064 2.063 0 1.139-.925 2.065-2.064 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/></svg></a>
              </div>
            </div>

            {/* Explore */}
            <div>
              <h4 className="text-white font-semibold mb-4 text-sm uppercase tracking-wider">Explore</h4>
              <ul className="space-y-3 text-sm">
                <li><Link to="/?type=rent" className="hover:text-emerald-400 transition">Rent a Home</Link></li>
                <li><Link to="/?type=sale" className="hover:text-emerald-400 transition">Buy a Home</Link></li>
                <li><Link to="/" className="hover:text-emerald-400 transition">All Listings</Link></li>
                <li><Link to="/" className="hover:text-emerald-400 transition">Neighbourhood Guides</Link></li>
              </ul>
            </div>

            {/* For Landlords */}
            <div>
              <h4 className="text-white font-semibold mb-4 text-sm uppercase tracking-wider">For Landlords</h4>
              <ul className="space-y-3 text-sm">
                <li><Link to="/dashboard/listings/new" className="hover:text-emerald-400 transition">List a Property</Link></li>
                <li><Link to="/verification" className="hover:text-emerald-400 transition">Get Verified</Link></li>
                <li><Link to="/wallet" className="hover:text-emerald-400 transition">Pricing & Plans</Link></li>
                <li><Link to="/settings" className="hover:text-emerald-400 transition">Payment Settings</Link></li>
              </ul>
            </div>

            {/* Support & Legal */}
            <div>
              <h4 className="text-white font-semibold mb-4 text-sm uppercase tracking-wider">Support</h4>
              <ul className="space-y-3 text-sm mb-6">
                <li><a href="#" className="hover:text-emerald-400 transition">Help Centre</a></li>
                <li><a href="#" className="hover:text-emerald-400 transition">Contact Us</a></li>
                <li><a href="#" className="hover:text-emerald-400 transition">Report a Problem</a></li>
              </ul>
              
              {/* Trust Signals */}
              <h4 className="text-white font-semibold mb-3 text-sm uppercase tracking-wider">Secure Payments</h4>
              <div className="flex gap-3 text-slate-500">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor"><path d="M12 0C5.373 0 0 5.373 0 12s5.373 12 12 12 12-5.373 12-12S18.627 0 12 0zm0 19c-3.866 0-7-3.134-7-7s3.134-7 7-7 7 3.134 7 7-3.134 7-7 7z"/></svg>
                <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor"><path d="M2 2h20v20H2z"/></svg>
                <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2z"/></svg>
              </div>
            </div>

          </div>

          {/* Bottom Bar */}
          <div className="border-t border-slate-800 pt-8 flex flex-col md:flex-row justify-between items-center gap-4 text-xs text-slate-500">
            <div className="flex gap-4">
              <a href="#" className="hover:text-white transition">Terms of Use</a>
              <a href="#" className="hover:text-white transition">Privacy Policy</a>
              <a href="#" className="hover:text-white transition">Cookie Policy</a>
            </div>
            <p className="text-center md:text-right">
              © {new Date().getFullYear()} NyumbaLink. All rights reserved. Made with ❤️ in Zambia.
            </p>
          </div>

        </div>
      </footer>
    </div>
  )
}
'''

LAYOUT_FILE.write_text(LAYOUT_CONTENT.strip() + "\n", encoding="utf-8")
print("Successfully replaced Layout.tsx with a rich, multi-column footer.")