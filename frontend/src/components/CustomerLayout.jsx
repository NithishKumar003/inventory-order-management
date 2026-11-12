import { Link, useNavigate, NavLink, Outlet, useLocation } from 'react-router-dom';
import {
  Store,
  ShoppingCart,
  Heart,
  Package,
  LogOut,
  Boxes,
  ArrowRight,
  Bell,
  LayoutGrid,
} from 'lucide-react';

const customerMenuItems = [
  { name: 'Store', path: '/store', icon: Store },
  { name: 'Shop', path: '/shop', icon: ShoppingCart },
  { name: 'Categories', path: '/categories', icon: LayoutGrid },
  { name: 'My Cart', path: '/cart', icon: ShoppingCart },
  { name: 'Wishlist', path: '/wishlist', icon: Heart },
  { name: 'My Orders', path: '/orders', icon: Package },
  { name: 'Notifications', path: '/notifications', icon: Bell },
];

export default function CustomerLayout({ onLogout }) {
  const location = useLocation();

  return (
    <div className="min-h-screen bg-slate-50 text-slate-800">
      {/* Main Header */}
      <header className="sticky top-0 z-40 border-b border-slate-200 bg-white/95 shadow-sm backdrop-blur-md">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-4 py-4 sm:px-6 lg:px-8">
          {/* Brand */}
          <NavLink
            to="/store"
            className="group flex items-center gap-3"
          >
            <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-blue-600 text-white shadow-lg shadow-blue-200 transition group-hover:scale-105">
              <Boxes size={24} />
            </div>

            <div>
              <h1 className="text-xl font-extrabold tracking-tight text-slate-900">
                Stock<span className="text-blue-600">Flow</span>
              </h1>
              <p className="text-xs text-slate-500">
                Your Shopping Space
              </p>
            </div>
          </NavLink>

          {/* Logout */}
          <button
            type="button"
            onClick={onLogout}
            className="flex items-center gap-2 rounded-xl border border-slate-200 px-3 py-2.5 text-sm font-semibold text-slate-600 transition hover:border-red-200 hover:bg-red-50 hover:text-red-600"
          >
            <LogOut size={17} />
            <span>Logout</span>
          </button>
        </div>
      </header>

      {/* Customer Navigation */}
      <nav className="sticky top-[76px] z-30 border-b border-slate-200 bg-white shadow-sm">
        <div className="mx-auto flex max-w-7xl gap-2 overflow-x-auto px-4 py-3 sm:px-6 lg:px-8">
          {customerMenuItems.map(({ name, path, icon: Icon }) => (
            <NavLink
              key={path}
              to={path}
              className={({ isActive }) =>
                `group flex shrink-0 items-center gap-2 rounded-xl px-4 py-2.5 text-sm font-semibold transition-all duration-200 ${
                  isActive
                    ? 'bg-blue-600 text-white shadow-md shadow-blue-100'
                    : 'text-slate-600 hover:bg-blue-50 hover:text-blue-700'
                }`
              }
            >
              <Icon size={18} />
              {name}
              {path === location.pathname && (
                <ArrowRight size={14} className="ml-1" />
              )}
            </NavLink>
          ))}
        </div>
      </nav>

      {/* Page Content */}
      <main className="mx-auto min-h-[calc(100vh-145px)] max-w-7xl px-4 py-6 sm:px-6 sm:py-8 lg:px-8">
        <div key={location.pathname} className="page-enter">
          <Outlet />
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-200 bg-white">
        <div className="mx-auto flex max-w-7xl flex-col items-center justify-between gap-2 px-4 py-5 text-xs text-slate-500 sm:flex-row sm:px-6 lg:px-8">
          <p>© {new Date().getFullYear()} StockFlow. All rights reserved.</p>
          <p>Simple shopping. Smooth experience.</p>
        </div>
      </footer>
    </div>
  );
}