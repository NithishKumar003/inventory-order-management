
import { useState } from 'react';
import { Link } from 'react-router-dom';
import {
  LockKeyhole,
  Mail,
  Package,
  Eye,
  EyeOff,
  ArrowRight,
  ShieldCheck,
  Boxes,
  Truck,
  AlertCircle,
  CheckCircle2,
  LoaderCircle,
} from 'lucide-react';

import api from '../services/api';

export default function Register() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');

  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [loading, setLoading] = useState(false);

  async function handleRegister(event) {
    event.preventDefault();
    setError('');
    setSuccess('');

    const trimmedEmail = email.trim();

    if (!trimmedEmail || !password || !confirmPassword) {
      setError('Please complete all fields.');
      return;
    }

    if (password.length < 8) {
      setError('Password must contain at least 8 characters.');
      return;
    }

    if (password !== confirmPassword) {
      setError('Passwords do not match.');
      return;
    }

    setLoading(true);

    try {
      await api.post('/auth/register', {
        email: trimmedEmail,
        password,
      });

      setSuccess('Account created successfully! You can now sign in.');
      setEmail('');
      setPassword('');
      setConfirmPassword('');
      setShowPassword(false);
      setShowConfirmPassword(false);
    } catch (error) {
      console.error(
        'Registration failed:',
        error.response?.data || error
      );

      setError(
        error.response?.data?.detail ||
        'Unable to create your account. Please try again.'
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-100 p-4 md:p-8">
      <div className="grid w-full max-w-6xl overflow-hidden rounded-3xl bg-white shadow-2xl lg:min-h-[680px] lg:grid-cols-2">

        {/* Left visual panel */}
        <section className="relative hidden flex-col justify-between overflow-hidden bg-gradient-to-br from-blue-700 via-blue-800 to-indigo-950 p-10 text-white lg:flex xl:p-14">
          <div className="absolute -right-24 -top-24 h-80 w-80 rounded-full border border-white/10" />
          <div className="absolute -bottom-32 -left-24 h-96 w-96 rounded-full border border-white/10" />

          <div className="relative z-10 flex items-center gap-3">
            <div className="rounded-xl bg-white/15 p-3">
              <Package size={27} />
            </div>
            <span className="text-xl font-bold tracking-wide">
              StockFlow
            </span>
          </div>

          <div className="relative z-10 max-w-md">
            <span className="rounded-full border border-white/20 bg-white/10 px-4 py-2 text-xs font-semibold uppercase tracking-widest text-blue-100">
              Join StockFlow
            </span>

            <h1 className="mt-7 text-4xl font-bold leading-tight xl:text-5xl">
              Start shopping with a simpler experience.
            </h1>

            <p className="mt-5 text-base leading-7 text-blue-100">
              Create your customer account and explore products,
              manage your cart, and keep track of your orders.
            </p>

            <div className="mt-10 space-y-5">
              <div className="flex items-center gap-4">
                <div className="rounded-xl bg-white/10 p-3">
                  <Boxes size={21} />
                </div>
                <div>
                  <p className="font-semibold">Explore products</p>
                  <p className="mt-1 text-sm text-blue-200">
                    Browse products in one convenient place.
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-4">
                <div className="rounded-xl bg-white/10 p-3">
                  <Truck size={21} />
                </div>
                <div>
                  <p className="font-semibold">Track your orders</p>
                  <p className="mt-1 text-sm text-blue-200">
                    Follow your orders through delivery.
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-4">
                <div className="rounded-xl bg-white/10 p-3">
                  <ShieldCheck size={21} />
                </div>
                <div>
                  <p className="font-semibold">Secure account</p>
                  <p className="mt-1 text-sm text-blue-200">
                    Protected authentication for your account.
                  </p>
                </div>
              </div>
            </div>
          </div>

          <p className="relative z-10 text-xs text-blue-200">
            StockFlow · Inventory and Order Management System
          </p>
        </section>

        {/* Registration form */}
        <section className="flex items-center justify-center px-6 py-10 sm:px-10 lg:px-12 xl:px-16">
          <div className="w-full max-w-md">

            <div className="mb-8 lg:hidden">
              <div className="flex items-center justify-center gap-3">
                <div className="rounded-xl bg-blue-600 p-3 text-white">
                  <Package size={26} />
                </div>
                <span className="text-2xl font-bold text-slate-900">
                  StockFlow
                </span>
              </div>
            </div>

            <div className="mb-7">
              <p className="text-sm font-semibold uppercase tracking-wider text-blue-600">
                Create your account
              </p>

              <h2 className="mt-2 text-3xl font-bold tracking-tight text-slate-900">
                Join StockFlow
              </h2>

              <p className="mt-3 text-sm leading-6 text-slate-500">
                Enter your details to create your customer account.
              </p>
            </div>

            <form onSubmit={handleRegister} className="space-y-4">
              {/* Email */}
              <div>
                <label
                  htmlFor="register-email"
                  className="mb-2 block text-sm font-semibold text-slate-700"
                >
                  Email address
                </label>

                <div className="flex items-center gap-3 rounded-xl border border-slate-200 bg-slate-50 px-4 transition focus-within:border-blue-500 focus-within:bg-white focus-within:ring-4 focus-within:ring-blue-50">
                  <Mail size={19} className="shrink-0 text-slate-400" />

                  <input
                    id="register-email"
                    type="email"
                    autoComplete="email"
                    required
                    disabled={loading}
                    value={email}
                    onChange={(event) => setEmail(event.target.value)}
                    placeholder="you@example.com"
                    className="w-full bg-transparent py-3.5 text-sm text-slate-800 outline-none placeholder:text-slate-400"
                  />
                </div>
              </div>

              {/* Password */}
              <div>
                <label
                  htmlFor="register-password"
                  className="mb-2 block text-sm font-semibold text-slate-700"
                >
                  Password
                </label>

                <div className="flex items-center gap-3 rounded-xl border border-slate-200 bg-slate-50 px-4 transition focus-within:border-blue-500 focus-within:bg-white focus-within:ring-4 focus-within:ring-blue-50">
                  <LockKeyhole size={19} className="shrink-0 text-slate-400" />

                  <input
                    id="register-password"
                    type={showPassword ? 'text' : 'password'}
                    autoComplete="new-password"
                    required
                    minLength={8}
                    disabled={loading}
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                    placeholder="Minimum 8 characters"
                    className="w-full bg-transparent py-3.5 text-sm text-slate-800 outline-none placeholder:text-slate-400"
                  />

                  <button
                    type="button"
                    disabled={loading}
                    onClick={() => setShowPassword((value) => !value)}
                    aria-label={showPassword ? 'Hide password' : 'Show password'}
                    className="shrink-0 text-slate-400 hover:text-slate-700"
                  >
                    {showPassword ? <EyeOff size={19} /> : <Eye size={19} />}
                  </button>
                </div>

                <p className="mt-1.5 text-xs text-slate-400">
                  Use at least 8 characters.
                </p>
              </div>

              {/* Confirm password */}
              <div>
                <label
                  htmlFor="confirm-password"
                  className="mb-2 block text-sm font-semibold text-slate-700"
                >
                  Confirm password
                </label>

                <div className="flex items-center gap-3 rounded-xl border border-slate-200 bg-slate-50 px-4 transition focus-within:border-blue-500 focus-within:bg-white focus-within:ring-4 focus-within:ring-blue-50">
                  <LockKeyhole size={19} className="shrink-0 text-slate-400" />

                  <input
                    id="confirm-password"
                    type={showConfirmPassword ? 'text' : 'password'}
                    autoComplete="new-password"
                    required
                    disabled={loading}
                    value={confirmPassword}
                    onChange={(event) => setConfirmPassword(event.target.value)}
                    placeholder="Re-enter your password"
                    className="w-full bg-transparent py-3.5 text-sm text-slate-800 outline-none placeholder:text-slate-400"
                  />

                  <button
                    type="button"
                    disabled={loading}
                    onClick={() => setShowConfirmPassword((value) => !value)}
                    aria-label={
                      showConfirmPassword
                        ? 'Hide confirmation password'
                        : 'Show confirmation password'
                    }
                    className="shrink-0 text-slate-400 hover:text-slate-700"
                  >
                    {showConfirmPassword
                      ? <EyeOff size={19} />
                      : <Eye size={19} />}
                  </button>
                </div>
              </div>

              {/* Error */}
              {error && (
                <div
                  role="alert"
                  className="flex items-start gap-3 rounded-xl border border-red-100 bg-red-50 p-4 text-sm text-red-700"
                >
                  <AlertCircle size={19} className="mt-0.5 shrink-0" />
                  <p>{error}</p>
                </div>
              )}

              {/* Success */}
              {success && (
                <div
                  role="status"
                  className="flex items-start gap-3 rounded-xl border border-emerald-100 bg-emerald-50 p-4 text-sm text-emerald-700"
                >
                  <CheckCircle2 size={19} className="mt-0.5 shrink-0" />
                  <div>
                    <p className="font-semibold">Registration successful</p>
                    <p className="mt-1">{success}</p>
                  </div>
                </div>
              )}

              <button
                type="submit"
                disabled={loading}
                className="flex w-full items-center justify-center gap-3 rounded-xl bg-blue-600 py-3.5 font-semibold text-white shadow-lg shadow-blue-600/20 hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-70"
              >
                {loading ? (
                  <>
                    <LoaderCircle size={19} className="animate-spin" />
                    Creating account...
                  </>
                ) : (
                  <>
                    Create Account
                    <ArrowRight size={19} />
                  </>
                )}
              </button>
            </form>

            <p className="mt-7 text-center text-sm text-slate-600">
              Already have an account?{' '}
              <Link
                to="/login"
                className="font-semibold text-blue-600 hover:text-blue-700"
              >
                Sign in
              </Link>
            </p>

            <div className="mt-7 flex items-center justify-center gap-2 text-xs text-slate-400">
              <ShieldCheck size={15} />
              Secure customer registration
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}
