import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import ErrorMessage from '../components/ErrorMessage'

export default function RegisterPage() {
  const { register } = useAuth()
  const navigate = useNavigate()

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [firstName, setFirstName] = useState('')
  const [lastName, setLastName] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    setError('')
    if (password.length < 8) {
      setError('Password must be at least 8 characters.')
      return
    }
    setSubmitting(true)
    try {
      await register(email, password, firstName, lastName)
      navigate('/', { replace: true })
    } catch (err) {
      setError((err as Error).message || 'Registration failed')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="max-w-md mx-auto px-4 py-16">
      <h1 className="text-2xl font-bold mb-6">Create your account</h1>
      {error && <ErrorMessage message={error} />}
      <form onSubmit={submit} className="space-y-4 bg-white p-6 rounded border">
        <div>
          <label className="block text-sm font-medium mb-1">Email</label>
          <input
            type="email" required value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full border rounded px-3 py-2 focus:ring-2 focus:ring-emerald-500 focus:outline-none"
          />
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium mb-1">First name</label>
            <input value={firstName} onChange={(e) => setFirstName(e.target.value)}
              className="w-full border rounded px-3 py-2 focus:ring-2 focus:ring-emerald-500 focus:outline-none" />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Last name</label>
            <input value={lastName} onChange={(e) => setLastName(e.target.value)}
              className="w-full border rounded px-3 py-2 focus:ring-2 focus:ring-emerald-500 focus:outline-none" />
          </div>
        </div>
        <div>
          <label className="block text-sm font-medium mb-1">Password</label>
          <input type="password" required value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full border rounded px-3 py-2 focus:ring-2 focus:ring-emerald-500 focus:outline-none" />
          <p className="text-xs text-gray-500 mt-1">At least 8 characters.</p>
        </div>
        <button type="submit" disabled={submitting}
          className="w-full bg-emerald-600 text-white py-2 rounded hover:bg-emerald-700 disabled:opacity-50">
          {submitting ? 'Creating account…' : 'Create account'}
        </button>
      </form>
      <p className="mt-6 text-sm text-center text-gray-600">
        Already have an account?{' '}
        <Link to="/login" className="text-emerald-700 hover:underline">Log in</Link>
      </p>
    </div>
  )
}
