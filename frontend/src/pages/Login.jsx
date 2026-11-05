
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
  LoaderCircle,
} from 'lucide-react';

import api from '../services/api';

export default function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  async function handleLogin(event) {
    event.preventDefault();
    setError('');

    const trimmedEmail = email.trim();

    if (!trimmedEmail || !password) {
      setError('Please enter your email and password.');
      return;
    }

    setLoading(true);

    try {
      const response = await api.post('/auth/login', {
        email: trimmedEmail,
        password,
      });

      const accessToken = response.data.access_token;

      if (!accessToken) {
        throw new Error('Login response did not contain an access token.');
      }

      localStorage.setItem('access_token', accessToken);

      window.location.replace('/');
    } catch (error) {
      console.error(
        'Login failed:',
        error.response?.data || error.message
      );

      if (error.response?.status === 401) {
        setError('Invalid email or password. Please try again.');
      } else if (error.response?.status === 403) {
        setError('Your account is inactive. Please contact the administrator.');
      } else {
        setError(
          error.response?.data?.detail ||
          error.message ||
          'Unable to log in. Please try again.'
        );
      }

      setLoading(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-100 p-4 md:p-8">
      <div className="grid w-full max-w-6xl overflow-hidden rounded-3xl bg-white shadow-2xl lg:min-h-[650px] lg:grid-cols-2">

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
              Inventory & Order Management
            </span>

            <h1 className="mt-7 text-4xl font-bold leading-tight xl:text-5xl">
              Manage your business with confidence.
            </h1>

            <p className="mt-5 text-base leading-7 text-blue-100">
              Keep products, inventory, and customer orders organized
              from one central workspace.
            </p>

            <div className="mt-10 space-y-5">
              <div className="flex items-center gap-4">
                <div className="rounded-xl bg-white/10 p-3">
                  <Boxes size={21} />
                </div>
                <div>
                  <p className="font-semibold">Inventory visibility</p>
                  <p className="mt-1 text-sm text-blue-200">
                    Keep track of stock and product availability.
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-4">
                <div className="rounded-xl bg-white/10 p-3">
                  <Truck size={21} />
                </div>
                <div>
                  <p className="font-semibold">Order management</p>
                  <p className="mt-1 text-sm text-blue-200">
                    Follow orders from confirmation to delivery.
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-4">
                <div className="rounded-xl bg-white/10 p-3">
                  <ShieldCheck size={21} />
                </div>
                <div>
                  <p className="font-semibold">Secure access</p>
                  <p className="mt-1 text-sm text-blue-200">
                    Protected sign-in using JWT authentication.
                  </p>
                </div>
              </div>
            </div>
          </div>

          <p className="relative z-10 text-xs text-blue-200">
            StockFlow · Inventory and Order Management System
          </p>
        </section>

        {/* Right login panel */}
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

            <div className="mb-8">
              <p className="text-sm font-semibold uppercase tracking-wider text-blue-600">
                Welcome back
              </p>

              <h2 className="mt-2 text-3xl font-bold tracking-tight text-slate-900">
                Sign in to your account
              </h2>

              <p className="mt-3 text-sm leading-6 text-slate-500">
                Enter your credentials to access your dashboard.
              </p>
            </div>

            <form onSubmit={handleLogin} className="space-y-5">
              <div>
                <label
                  htmlFor="email"
                  className="mb-2 block text-sm font-semibold text-slate-700"
                >
                  Email address
                </label>

                <div className="flex items-center gap-3 rounded-xl border border-slate-200 bg-slate-50 px-4 transition focus-within:border-blue-500 focus-within:bg-white focus-within:ring-4 focus-within:ring-blue-50">
                  <Mail size={19} className="shrink-0 text-slate-400" />

                  <input
                    id="email"
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

              <div>
                <div className="mb-2 flex items-center justify-between">
                  <label
                    htmlFor="password"
                    className="block text-sm font-semibold text-slate-700"
                  >
                    Password
                  </label>
                </div>

                <div className="flex items-center gap-3 rounded-xl border border-slate-200 bg-slate-50 px-4 transition focus-within:border-blue-500 focus-within:bg-white focus-within:ring-4 focus-within:ring-blue-50">
                  <LockKeyhole size={19} className="shrink-0 text-slate-400" />

                  <input
                    id="password"
                    type={showPassword ? 'text' : 'password'}
                    autoComplete="current-password"
                    required
                    disabled={loading}
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                    placeholder="Enter your password"
                    className="w-full bg-transparent py-3.5 text-sm text-slate-800 outline-none placeholder:text-slate-400"
                  />

                  <button
                    type="button"
                    onClick={() => setShowPassword((value) => !value)}
                    disabled={loading}
                    aria-label={showPassword ? 'Hide password' : 'Show password'}
                    className="shrink-0 text-slate-400 hover:text-slate-700"
                  >
                    {showPassword ? <EyeOff size={19} /> : <Eye size={19} />}
                  </button>
                </div>
              </div>

              {error && (
                <div
                  role="alert"
                  className="flex items-start gap-3 rounded-xl border border-red-100 bg-red-50 p-4 text-sm text-red-700"
                >
                  <AlertCircle size={19} className="mt-0.5 shrink-0" />
                  <p>{error}</p>
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
                    Signing in...
                  </>
                ) : (
                  <>
                    Sign In
                    <ArrowRight size={19} />
                  </>
                )}
              </button>
            </form>

            <div className="my-7 flex items-center gap-3">
              <div className="h-px flex-1 bg-slate-200" />
              <span className="text-xs text-slate-400">NEW TO STOCKFLOW?</span>
              <div className="h-px flex-1 bg-slate-200" />
            </div>

            <Link
              to="/register"
              className="block w-full rounded-xl border border-slate-200 py-3.5 text-center text-sm font-semibold text-slate-700 hover:border-blue-300 hover:bg-blue-50 hover:text-blue-700"
            >
              Create a new account
            </Link>

            <div className="mt-8 flex items-center justify-center gap-2 text-xs text-slate-400">
              <ShieldCheck size={15} />
              Secure authentication powered by JWT
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}
