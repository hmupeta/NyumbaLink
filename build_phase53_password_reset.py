#!/usr/bin/env python3
"""NyumbaLink Phase 53: Forgot Password & Secure Account Recovery."""
from __future__ import annotations
import subprocess
from pathlib import Path

ROOT = Path.cwd()
FRONTEND = ROOT / "frontend"
MOBILE = ROOT / "mobile"
LIB = MOBILE / "lib"

# ----------------------------------------------------------------
# 1. Backend: Password Reset Views
# ----------------------------------------------------------------
ACCOUNTS_VIEWS = ROOT / "apps" / "accounts" / "views.py"
text = ACCOUNTS_VIEWS.read_text(encoding="utf-8")

if "class PasswordResetRequestView" not in text:
    password_reset_code = '''

# ---------- PASSWORD RESET ----------
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import send_mail
from django.conf import settings as django_settings
from .models import User as UserModel


class PasswordResetRequestView(APIView):
    """Step 1: User submits email. We send a reset link with a short-lived token."""
    permission_classes = [AllowAny]

    def post(self, request):
        email = (request.data.get("email") or "").lower().strip()
        if not email:
            return Response({"detail": "Email is required."}, status=400)

        user = UserModel.objects.filter(email=email).first()
        
        # Always return 200 to prevent email enumeration attacks.
        if not user:
            return Response({"detail": "If the email exists, a reset link has been sent."}, status=200)

        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        reset_url = f"{request.data.get('origin', 'http://localhost:5173')}/reset-password/{uid}/{token}"

        subject = "Reset your NyumbaLink password"
        message = f"""
Hello {user.first_name or user.email},

Someone requested a password reset for your NyumbaLink account.
If this was you, click the link below to set a new password:

{reset_url}

This link expires in 1 hour. If you didn't request this, you can safely ignore this email.

— The NyumbaLink Team
        """.strip()

        try:
            send_mail(subject, message, django_settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=True)
        except Exception:
            pass  # Silent fail — email issues shouldn't leak account existence

        return Response({"detail": "If the email exists, a reset link has been sent."}, status=200)


class PasswordResetConfirmView(APIView):
    """Step 2: User submits uid + token + new password from the email link."""
    permission_classes = [AllowAny]

    def post(self, request):
        uid_b64 = request.data.get("uid")
        token = request.data.get("token")
        new_password = request.data.get("password")

        if not all([uid_b64, token, new_password]):
            return Response({"detail": "Missing fields."}, status=400)

        if len(new_password) < 8:
            return Response({"detail": "Password must be at least 8 characters."}, status=400)

        try:
            uid = force_str(urlsafe_base64_decode(uid_b64))
            user = UserModel.objects.get(pk=uid)
        except (UserModel.DoesNotExist, ValueError, TypeError):
            return Response({"detail": "Invalid reset link."}, status=400)

        if not default_token_generator.check_token(user, token):
            return Response({"detail": "This reset link has expired or is invalid."}, status=400)

        user.set_password(new_password)
        user.save()

        return Response({"detail": "Password reset successfully. Please log in."}, status=200)
'''
    
    text += password_reset_code
    ACCOUNTS_VIEWS.write_text(text, encoding="utf-8")
    print("✅ Patched apps/accounts/views.py: Added Password Reset views")

# ----------------------------------------------------------------
# 2. Backend: Wire up URLs
# ----------------------------------------------------------------
ACCOUNTS_URLS = ROOT / "apps" / "accounts" / "urls.py"
text = ACCOUNTS_URLS.read_text(encoding="utf-8")

if "password-reset" not in text:
    text = text.replace(
        "from .views import LoginView, LogoutView, MeView, RefreshView, RegisterView",
        "from .views import LoginView, LogoutView, MeView, RefreshView, RegisterView, PasswordResetRequestView, PasswordResetConfirmView"
    )
    text = text.replace(
        'path("me/", MeView.as_view(), name="auth-me"),',
        'path("me/", MeView.as_view(), name="auth-me"),\n    path("password-reset/", PasswordResetRequestView.as_view(), name="auth-password-reset"),\n    path("password-reset/confirm/", PasswordResetConfirmView.as_view(), name="auth-password-reset-confirm"),'
    )
    ACCOUNTS_URLS.write_text(text, encoding="utf-8")
    print("✅ Patched apps/accounts/urls.py: Wired password reset endpoints")

print("\n🚀 Pushing backend to GitHub...")
subprocess.run(["git", "add", "."], cwd=ROOT)
subprocess.run(["git", "commit", "-m", "Feat: Add password reset endpoints"], cwd=ROOT)
subprocess.run(["git", "push", "origin", "main"], cwd=ROOT)

# ----------------------------------------------------------------
# 3. Web: API Client Update
# ----------------------------------------------------------------
WEB_AUTH_API = FRONTEND / "src" / "api" / "auth.ts"
text = WEB_AUTH_API.read_text(encoding="utf-8")

if "resetPassword" not in text:
    text = text.replace(
        "  me: () => api<User>('/auth/me/'),",
        '''  me: () => api<User>('/auth/me/'),
  requestPasswordReset: (email: string, origin: string) => api('/auth/password-reset/', {
    method: 'POST',
    body: JSON.stringify({ email, origin }),
  }),
  resetPassword: (uid: string, token: string, password: string) => api('/auth/password-reset/confirm/', {
    method: 'POST',
    body: JSON.stringify({ uid, token, password }),
  }),'''
    )
    WEB_AUTH_API.write_text(text, encoding="utf-8")
    print("✅ Patched frontend src/api/auth.ts: Added password reset methods")

# ----------------------------------------------------------------
# 4. Web: Forgot Password Page
# ----------------------------------------------------------------
FORGOT_PAGE = '''
import { useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { authApi } from '../api/auth'

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('')
  const [submitted, setSubmitted] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await authApi.requestPasswordReset(email, window.location.origin)
      setSubmitted(true)
    } catch (err) {
      setError((err as Error).message)
    }
    setLoading(false)
  }

  if (submitted) {
    return (
      <div className="max-w-md mx-auto px-4 py-16">
        <div className="bg-white p-8 rounded-lg border shadow-sm text-center">
          <div className="w-16 h-16 rounded-full bg-green-100 mx-auto mb-4 flex items-center justify-center">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#059669" strokeWidth="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>
          </div>
          <h1 className="text-xl font-bold mb-2">Check your email</h1>
          <p className="text-gray-600 text-sm mb-6">
            If an account exists for <strong>{email}</strong>, we've sent a link to reset your password.
          </p>
          <Link to="/login" className="text-emerald-700 hover:underline text-sm">Back to login</Link>
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-md mx-auto px-4 py-16">
      <h1 className="text-2xl font-bold mb-2">Forgot password?</h1>
      <p className="text-gray-600 mb-6 text-sm">Enter your email and we'll send you a reset link.</p>
      {error && <div className="bg-red-50 text-red-700 p-3 rounded mb-4 text-sm">{error}</div>}
      <form onSubmit={submit} className="bg-white p-6 rounded-lg border space-y-4">
        <div>
          <label className="block text-sm font-medium mb-1">Email address</label>
          <input
            type="email" required value={email}
            onChange={e => setEmail(e.target.value)}
            className="w-full border rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-emerald-500"
          />
        </div>
        <button
          type="submit" disabled={loading}
          className="w-full bg-emerald-600 text-white py-2 rounded hover:bg-emerald-700 disabled:opacity-50 font-medium"
        >
          {loading ? 'Sending...' : 'Send reset link'}
        </button>
      </form>
      <p className="mt-6 text-sm text-center text-gray-600">
        Remembered it? <Link to="/login" className="text-emerald-700 hover:underline">Log in</Link>
      </p>
    </div>
  )
}
'''
(FRONTEND / "src" / "pages" / "ForgotPasswordPage.tsx").write_text(FORGOT_PAGE.strip() + "\n", encoding="utf-8")
print("✅ Created frontend ForgotPasswordPage.tsx")

# ----------------------------------------------------------------
# 5. Web: Reset Password Page
# ----------------------------------------------------------------
RESET_PAGE = '''
import { useState, type FormEvent } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { authApi } from '../api/auth'

export default function ResetPasswordPage() {
  const { uid, token } = useParams<{ uid: string; token: string }>()
  const navigate = useNavigate()
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [success, setSuccess] = useState(false)

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    setError('')
    if (password.length < 8) return setError('Password must be at least 8 characters.')
    if (password !== confirm) return setError('Passwords do not match.')

    setLoading(true)
    try {
      await authApi.resetPassword(uid!, token!, password)
      setSuccess(true)
      setTimeout(() => navigate('/login'), 2500)
    } catch (err) {
      setError((err as Error).message)
    }
    setLoading(false)
  }

  if (success) {
    return (
      <div className="max-w-md mx-auto px-4 py-16">
        <div className="bg-white p-8 rounded-lg border shadow-sm text-center">
          <div className="w-16 h-16 rounded-full bg-green-100 mx-auto mb-4 flex items-center justify-center">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#059669" strokeWidth="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>
          </div>
          <h1 className="text-xl font-bold mb-2">Password reset!</h1>
          <p className="text-gray-600 text-sm">Redirecting you to login...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-md mx-auto px-4 py-16">
      <h1 className="text-2xl font-bold mb-6">Set a new password</h1>
      {error && <div className="bg-red-50 text-red-700 p-3 rounded mb-4 text-sm">{error}</div>}
      <form onSubmit={submit} className="bg-white p-6 rounded-lg border space-y-4">
        <div>
          <label className="block text-sm font-medium mb-1">New password</label>
          <input type="password" required value={password}
            onChange={e => setPassword(e.target.value)}
            className="w-full border rounded px-3 py-2" />
        </div>
        <div>
          <label className="block text-sm font-medium mb-1">Confirm password</label>
          <input type="password" required value={confirm}
            onChange={e => setConfirm(e.target.value)}
            className="w-full border rounded px-3 py-2" />
        </div>
        <button type="submit" disabled={loading}
          className="w-full bg-emerald-600 text-white py-2 rounded hover:bg-emerald-700 font-medium disabled:opacity-50">
          {loading ? 'Resetting...' : 'Reset password'}
        </button>
      </form>
      <p className="mt-6 text-sm text-center text-gray-600">
        <Link to="/login" className="text-emerald-700 hover:underline">Back to login</Link>
      </p>
    </div>
  )
}
'''
(FRONTEND / "src" / "pages" / "ResetPasswordPage.tsx").write_text(RESET_PAGE.strip() + "\n", encoding="utf-8")
print("✅ Created frontend ResetPasswordPage.tsx")

# ----------------------------------------------------------------
# 6. Web: Add "Forgot password?" link to Login page
# ----------------------------------------------------------------
LOGIN_PAGE = FRONTEND / "src" / "pages" / "LoginPage.tsx"
text = LOGIN_PAGE.read_text(encoding="utf-8")

if "Forgot password" not in text:
    # Find the password input block and add a link
    text = text.replace(
        '''          <label className="block text-sm font-medium mb-1">Password</label>''',
        '''          <div className="flex justify-between items-center mb-1">
            <label className="block text-sm font-medium">Password</label>
            <Link to="/forgot-password" className="text-xs text-emerald-700 hover:underline">Forgot password?</Link>
          </div>'''
    )
    LOGIN_PAGE.write_text(text, encoding="utf-8")
    print("✅ Patched LoginPage.tsx: Added Forgot password link")

# ----------------------------------------------------------------
# 7. Web: Wire routes into App.tsx
# ----------------------------------------------------------------
APP_TSX = FRONTEND / "src" / "App.tsx"
text = APP_TSX.read_text(encoding="utf-8")

if "ForgotPasswordPage" not in text:
    text = text.replace(
        "import LoginPage from './pages/LoginPage'",
        "import LoginPage from './pages/LoginPage'\nimport ForgotPasswordPage from './pages/ForgotPasswordPage'\nimport ResetPasswordPage from './pages/ResetPasswordPage'"
    )
    text = text.replace(
        '<Route path="/login" element={<LoginPage />} />',
        '<Route path="/login" element={<LoginPage />} />\n        <Route path="/forgot-password" element={<ForgotPasswordPage />} />\n        <Route path="/reset-password/:uid/:token" element={<ResetPasswordPage />} />'
    )
    APP_TSX.write_text(text, encoding="utf-8")
    print("✅ Patched App.tsx: Mounted password reset routes")

# ----------------------------------------------------------------
# 8. Mobile: API Client
# ----------------------------------------------------------------
MOBILE_API = LIB / "api_client.dart"
text = MOBILE_API.read_text(encoding="utf-8")

if "requestPasswordReset" not in text:
    text = text.replace(
        "  // --- Saved Properties ---",
        '''  static Future<void> requestPasswordReset(String email) async {
    final res = await http.post(
      Uri.parse('$baseUrl/auth/password-reset/'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'email': email, 'origin': 'https://nyumbalink-frontend-pbkm.onrender.com'}),
    );
    if (res.statusCode != 200) throw Exception('Failed to send reset link');
  }

  // --- Saved Properties ---'''
    )
    MOBILE_API.write_text(text, encoding="utf-8")
    print("✅ Patched mobile api_client.dart: Added requestPasswordReset")

# ----------------------------------------------------------------
# 9. Mobile: Forgot Password Screen
# ----------------------------------------------------------------
FORGOT_SCREEN = '''
import 'package:flutter/material.dart';
import 'api_client.dart';

class ForgotPasswordScreen extends StatefulWidget {
  @override
  _ForgotPasswordScreenState createState() => _ForgotPasswordScreenState();
}

class _ForgotPasswordScreenState extends State<ForgotPasswordScreen> {
  final _emailCtrl = TextEditingController();
  bool _submitted = false;
  bool _loading = false;
  String? _error;

  void _submit() async {
    if (_emailCtrl.text.trim().isEmpty) return;
    setState(() { _loading = true; _error = null; });
    try {
      await ApiClient.requestPasswordReset(_emailCtrl.text.trim());
      setState(() { _submitted = true; });
    } catch (e) {
      setState(() { _error = e.toString(); });
    }
    setState(() { _loading = false; });
  }

  @override
  Widget build(BuildContext context) {
    if (_submitted) {
      return Scaffold(
        appBar: AppBar(title: Text("Forgot Password"), backgroundColor: Color(0xFF059669)),
        body: Padding(
          padding: EdgeInsets.all(24),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(Icons.mark_email_read, size: 80, color: Colors.green),
              SizedBox(height: 16),
              Text("Check your email", style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold)),
              SizedBox(height: 8),
              Text("We've sent a password reset link to ${_emailCtrl.text}. Open the link on a device with a browser to reset your password.",
                textAlign: TextAlign.center, style: TextStyle(color: Colors.grey)),
              SizedBox(height: 32),
              TextButton(onPressed: () => Navigator.pop(context), child: Text("Back to Login")),
            ],
          ),
        ),
      );
    }

    return Scaffold(
      appBar: AppBar(title: Text("Forgot Password"), backgroundColor: Color(0xFF059669)),
      body: Padding(
        padding: EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text("Reset your password", style: TextStyle(fontSize: 22, fontWeight: FontWeight.bold)),
            SizedBox(height: 8),
            Text("Enter the email address associated with your account.", style: TextStyle(color: Colors.grey)),
            SizedBox(height: 24),
            if (_error != null) Container(
              padding: EdgeInsets.all(12),
              decoration: BoxDecoration(color: Colors.red[50], borderRadius: BorderRadius.circular(8)),
              child: Text(_error!, style: TextStyle(color: Colors.red[800])),
            ),
            SizedBox(height: 12),
            TextField(
              controller: _emailCtrl,
              keyboardType: TextInputType.emailAddress,
              decoration: InputDecoration(labelText: "Email", border: OutlineInputBorder()),
            ),
            SizedBox(height: 16),
            SizedBox(
              width: double.infinity,
              height: 50,
              child: ElevatedButton(
                onPressed: _loading ? null : _submit,
                style: ElevatedButton.styleFrom(backgroundColor: Color(0xFF059669)),
                child: _loading ? CircularProgressIndicator(color: Colors.white) : Text("Send Reset Link"),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
'''
(LIB / "forgot_password_screen.dart").write_text(FORGOT_SCREEN.strip() + "\n", encoding="utf-8")
print("✅ Created mobile forgot_password_screen.dart")

# ----------------------------------------------------------------
# 10. Mobile: Add "Forgot password?" link to Login screen
# ----------------------------------------------------------------
LOGIN_MOBILE = LIB / "login_screen.dart"
text = LOGIN_MOBILE.read_text(encoding="utf-8")

if "ForgotPasswordScreen" not in text:
    text = text.replace(
        "import 'main_layout.dart';",
        "import 'main_layout.dart';\nimport 'forgot_password_screen.dart';"
    )
    
    # Add the link right below the password field
    text = text.replace(
        '''              TextField(controller: _passCtrl, decoration: InputDecoration(labelText: 'Password', border: OutlineInputBorder()), obscureText: true),
              SizedBox(height: 24),''',
        '''              TextField(controller: _passCtrl, decoration: InputDecoration(labelText: 'Password', border: OutlineInputBorder()), obscureText: true),
              Align(
                alignment: Alignment.centerRight,
                child: TextButton(
                  onPressed: () => Navigator.push(context, MaterialPageRoute(builder: (_) => ForgotPasswordScreen())),
                  child: Text("Forgot password?", style: TextStyle(color: Color(0xFF059669))),
                ),
              ),
              SizedBox(height: 8),'''
    )
    LOGIN_MOBILE.write_text(text, encoding="utf-8")
    print("✅ Patched mobile login_screen.dart: Added Forgot password link")

# ----------------------------------------------------------------
# 11. Push frontend + mobile
# ----------------------------------------------------------------
print("\n🚀 Committing and pushing to GitHub...")
subprocess.run(["git", "add", "."], cwd=ROOT)
subprocess.run(["git", "commit", "-m", "Feat: Add password reset flow (web + mobile)"], cwd=ROOT)
subprocess.run(["git", "push", "origin", "main"], cwd=ROOT)

print("""
==================================================
🎉 PHASE 53 COMPLETE: PASSWORD RECOVERY
==================================================

### How to test:
1. **Web**: Go to /login → click "Forgot password?" → enter your email.
2. If Resend is configured, you'll get a real email. Otherwise check the Render backend logs — the reset link is printed there (fail_silently=True).
3. Click the link — it opens /reset-password/<uid>/<token>.
4. Enter a new password, submit, and you're redirected to login.
5. Log in with the new password. ✅

### Mobile:
1. Restart Flutter (`q`, then `flutter run -d chrome`).
2. Go to Profile → Login → click "Forgot password?"
3. Enter your email. The app will show "Check your email".
4. Since the reset link opens in a browser, complete the reset on the web, then log back in on mobile with the new password.
""")