import { Link, NavLink, Outlet, useLocation } from 'react-router-dom';
import {
  LayoutDashboard,
  Star,
  Package,
  Boxes,
  ShoppingCart,
  Users,
  Truck,
  RotateCcw,
  BarChart3,
  Settings,
  Bell,
  Search,
  ChevronDown,
  LogOut,
} from 'lucide-react';

const menuItems = [
  { name: 'Dashboard', path: '/', icon: LayoutDashboard },
  { name: 'Products', path: '/products', icon: Package },
  { name: 'Inventory', path: '/inventory', icon: Boxes },
  { name: 'Orders', path: '/orders', icon: ShoppingCart },
  { name: 'Customers', path: '/customers', icon: Users },
  { name: 'Deliveries', path: '/deliveries', icon: Truck },
  { name: 'Returns', path: '/returns', icon: RotateCcw },
  { name: 'Reviews', path: '/reviews', icon: Star },
  { name: 'Reports', path: '/reports', icon: BarChart3 },
  { name: 'Notifications', path: '/notifications', icon: Bell },
];

export default function Layout({ onLogout }) {
  const location = useLocation();

  return (
    <div className="flex min-h-screen bg-slate-50 text-slate-800">
      {/* Admin Sidebar */}
      <aside className="sticky top-0 hidden h-screen w-64 shrink-0 flex-col bg-slate-950 text-white md:flex">
        <div className="border-b border-slate-800 px-6 py-7">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-600 shadow-lg shadow-blue-900/30">
              <Boxes size={23} />
            </div>
            <div>
              <h1 className="text-xl font-bold tracking-tight">StockFlow</h1>
              <p className="mt-1 text-xs text-slate-400">
                Inventory Management
              </p>
            </div>
          </div>
        </div>

        <div className="px-5 pb-2 pt-7">
          <p className="text-xs font-semibold uppercase tracking-widest text-slate-500">
            Workspace
          </p>
        </div>

        <nav className="flex-1 space-y-1 overflow-y-auto px-3 py-2">
          {menuItems.map(({ name, path, icon: Icon }) => (
            <NavLink
              key={name}
              to={path}
              end={path === '/'}
              className={({ isActive }) =>
                `group flex w-full items-center gap-3 rounded-xl px-4 py-3 text-sm font-medium transition-all duration-200 ${
                  isActive
                    ? 'bg-blue-600 text-white shadow-lg shadow-blue-950/30'
                    : 'text-slate-400 hover:translate-x-1 hover:bg-slate-800 hover:text-white'
                }`
              }
            >
              <Icon size={19} className="shrink-0" />
              {name}
            </NavLink>
          ))}
        </nav>

        <div className="border-t border-slate-800 p-4">
          <NavLink
            to="/settings"
            className={({ isActive }) =>
              `flex w-full items-center gap-3 rounded-xl px-4 py-3 text-sm transition ${
                isActive
                  ? 'bg-blue-600 text-white'
                  : 'text-slate-400 hover:bg-slate-800 hover:text-white'
              }`
            }
          >
            <Settings size={19} />
            Settings
          </NavLink>

          <p className="mt-4 px-4 text-xs text-slate-600">
            StockFlow Admin Workspace
          </p>
        </div>
      </aside>

      {/* Main Workspace */}
      <main className="min-w-0 flex-1">
        {/* Sticky Header */}
        <header className="sticky top-0 z-30 flex flex-wrap items-center justify-between gap-4 border-b border-slate-200 bg-white/95 px-5 py-4 shadow-sm backdrop-blur-md md:px-8">
          <div>
            <h2 className="text-xl font-bold tracking-tight text-slate-900">
              StockFlow Workspace
            </h2>
            <p className="mt-1 text-sm text-slate-500">
              Inventory and order management
            </p>
          </div>

          <div className="flex items-center gap-3 sm:gap-4">
            {/* Search */}
            <div className="hidden items-center gap-2 rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 transition focus-within:border-blue-400 focus-within:bg-white focus-within:ring-2 focus-within:ring-blue-100 sm:flex">
              <Search size={17} className="text-slate-400" />
              <input
                aria-label="Search"
                placeholder="Search..."
                className="w-28 bg-transparent text-sm outline-none placeholder:text-slate-400"
              />
            </div>

            {/* Notifications */}
            <Link
              to="/notifications"
              aria-label="Notifications"
              className="relative rounded-xl p-2.5 text-slate-600 transition hover:bg-blue-50 hover:text-blue-700"
            >
              <Bell size={20} />
            </Link>

            {/* Admin Profile */}
            <div className="hidden items-center gap-2 rounded-xl px-2 py-1.5 sm:flex">
              <div className="flex h-9 w-9 items-center justify-center rounded-full bg-blue-100 font-bold text-blue-700">
                A
              </div>
              <div>
                <p className="text-sm font-semibold text-slate-800">
                  Admin
                </p>
                <p className="text-xs text-slate-500">Administrator</p>
              </div>
              <ChevronDown size={16} className="text-slate-400" />
            </div>

            {/* Logout */}
            <button
              type="button"
              onClick={onLogout}
              className="flex items-center gap-2 rounded-xl border border-slate-200 px-3 py-2.5 text-sm font-semibold text-slate-600 transition hover:border-red-200 hover:bg-red-50 hover:text-red-600"
            >
              <LogOut size={17} />
              <span className="hidden sm:inline">Logout</span>
            </button>
          </div>
        </header>

        {/* Animated Page Content */}
        <div key={location.pathname} className="page-enter">
          <Outlet />
        </div>
      </main>
    </div>
  );
}