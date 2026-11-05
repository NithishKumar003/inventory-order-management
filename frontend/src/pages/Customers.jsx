
import { useEffect, useMemo, useState } from 'react';
import {
  Users,
  UserCheck,
  UserX,
  RefreshCw,
  Search,
  Mail,
  ShieldCheck,
  CalendarDays,
  UserRound,
  UsersRound,
} from 'lucide-react';
import api from '../services/api';

function formatDate(value) {
  if (!value) return '—';

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) return '—';

  return date.toLocaleDateString('en-IN', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  });
}

function StatusBadge({ active }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-semibold ${
        active
          ? 'bg-emerald-50 text-emerald-700'
          : 'bg-red-50 text-red-700'
      }`}
    >
      <span
        className={`h-1.5 w-1.5 rounded-full ${
          active ? 'bg-emerald-500' : 'bg-red-500'
        }`}
      />
      {active ? 'Active' : 'Inactive'}
    </span>
  );
}

function RoleBadge({ role }) {
  const isAdmin = String(role || '').toLowerCase() === 'admin';

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-xs font-semibold ${
        isAdmin
          ? 'bg-violet-50 text-violet-700'
          : 'bg-blue-50 text-blue-700'
      }`}
    >
      {isAdmin ? <ShieldCheck size={13} /> : <UserRound size={13} />}
      {role || 'Unknown'}
    </span>
  );
}

function LoadingSkeleton() {
  return (
    <div className="space-y-3 p-5">
      {[1, 2, 3, 4, 5].map((item) => (
        <div
          key={item}
          className="h-16 animate-pulse rounded-xl bg-slate-100"
        />
      ))}
    </div>
  );
}

function StatCard({ title, value, description, icon: Icon, color }) {
  const colors = {
    blue: 'bg-blue-50 text-blue-600',
    green: 'bg-emerald-50 text-emerald-600',
    red: 'bg-red-50 text-red-600',
  };

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition duration-200 hover:-translate-y-1 hover:shadow-md">
      <div className="flex items-center justify-between">
        <p className="text-sm font-medium text-slate-500">{title}</p>
        <div className={`rounded-xl p-3 ${colors[color]}`}>
          <Icon size={21} />
        </div>
      </div>

      <p className="mt-4 text-3xl font-bold tracking-tight text-slate-900">
        {value}
      </p>

      <p className="mt-1 text-xs text-slate-400">{description}</p>
    </div>
  );
}

export default function Customers() {
  const [customers, setCustomers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');

  async function loadCustomers() {
    setLoading(true);
    setError('');

    try {
      const response = await api.get('/auth/admin/customers');

      setCustomers(
        Array.isArray(response.data) ? response.data : []
      );
    } catch (err) {
      setError(
        err.response?.data?.detail ||
        'Unable to load customers. Please try again.'
      );
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadCustomers();
  }, []);

  const activeCustomers = customers.filter(
    (customer) => customer.is_active
  ).length;

  const inactiveCustomers = customers.length - activeCustomers;

  const filteredCustomers = useMemo(() => {
    return customers.filter((customer) => {
      const searchValue = search.trim().toLowerCase();

      const matchesSearch =
        !searchValue ||
        String(customer.id).toLowerCase().includes(searchValue) ||
        String(customer.email || '').toLowerCase().includes(searchValue) ||
        String(customer.role || '').toLowerCase().includes(searchValue);

      const matchesStatus =
        statusFilter === 'all' ||
        (statusFilter === 'active' && customer.is_active) ||
        (statusFilter === 'inactive' && !customer.is_active);

      return matchesSearch && matchesStatus;
    });
  }, [customers, search, statusFilter]);

  return (
    <section className="min-h-screen space-y-7 p-4 md:p-7">
      {/* Heading */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="mb-2 flex items-center gap-2 text-sm font-medium text-blue-600">
            <Users size={16} />
            User Management
          </div>

          <h1 className="text-3xl font-bold tracking-tight text-slate-900">
            Customers
          </h1>

          <p className="mt-2 text-sm text-slate-500">
            View and monitor registered customer accounts.
          </p>
        </div>

        <button
          type="button"
          onClick={loadCustomers}
          disabled={loading}
          className="inline-flex items-center gap-2 rounded-xl bg-slate-900 px-5 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-50"
        >
          <RefreshCw
            size={16}
            className={loading ? 'animate-spin' : ''}
          />
          {loading ? 'Refreshing...' : 'Refresh'}
        </button>
      </div>

      {/* Error */}
      {error && (
        <div
          role="alert"
          className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700"
        >
          <p>{error}</p>

          <button
            type="button"
            onClick={loadCustomers}
            className="font-semibold underline"
          >
            Try again
          </button>
        </div>
      )}

      {/* Statistics */}
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        <StatCard
          title="Total customers"
          value={loading ? '—' : customers.length.toLocaleString('en-IN')}
          description="All registered accounts"
          icon={UsersRound}
          color="blue"
        />

        <StatCard
          title="Active accounts"
          value={loading ? '—' : activeCustomers.toLocaleString('en-IN')}
          description="Accounts currently active"
          icon={UserCheck}
          color="green"
        />

        <StatCard
          title="Inactive accounts"
          value={loading ? '—' : inactiveCustomers.toLocaleString('en-IN')}
          description="Accounts currently inactive"
          icon={UserX}
          color="red"
        />
      </div>

      {/* Customer list */}
      <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-100 p-5 md:p-6">
          <div>
            <h2 className="text-lg font-bold text-slate-900">
              Registered customers
            </h2>
            <p className="mt-1 text-sm text-slate-500">
              Customer accounts retrieved from the Auth Service.
            </p>
          </div>

          <span className="rounded-full bg-blue-50 px-3 py-1.5 text-xs font-semibold text-blue-700">
            {loading ? 'Loading...' : `${filteredCustomers.length} customers`}
          </span>
        </div>

        {/* Search and filters */}
        <div className="flex flex-col gap-3 border-b border-slate-100 p-4 md:flex-row md:items-center md:justify-between">
          <div className="relative w-full md:max-w-sm">
            <Search
              size={17}
              className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"
            />

            <input
              type="text"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search by email, ID or role..."
              className="w-full rounded-xl border border-slate-200 bg-slate-50 py-2.5 pl-10 pr-4 text-sm outline-none transition focus:border-blue-400 focus:bg-white focus:ring-4 focus:ring-blue-50"
            />
          </div>

          <div className="flex flex-wrap gap-2">
            {[
              { value: 'all', label: 'All customers' },
              { value: 'active', label: 'Active' },
              { value: 'inactive', label: 'Inactive' },
            ].map((filter) => (
              <button
                key={filter.value}
                type="button"
                onClick={() => setStatusFilter(filter.value)}
                className={`rounded-lg px-3 py-2 text-xs font-semibold transition ${
                  statusFilter === filter.value
                    ? 'bg-slate-900 text-white shadow-sm'
                    : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                }`}
              >
                {filter.label}
              </button>
            ))}
          </div>
        </div>

        {loading ? (
          <LoadingSkeleton />
        ) : !error && filteredCustomers.length === 0 ? (
          <div className="px-5 py-16 text-center">
            <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-slate-100 text-slate-400">
              <Users size={26} />
            </div>

            <h3 className="mt-4 font-semibold text-slate-800">
              {customers.length === 0
                ? 'No customers registered'
                : 'No matching customers'}
            </h3>

            <p className="mt-1 text-sm text-slate-500">
              {customers.length === 0
                ? 'Registered customer accounts will appear here.'
                : 'Try changing your search or status filter.'}
            </p>

            {(search || statusFilter !== 'all') && (
              <button
                type="button"
                onClick={() => {
                  setSearch('');
                  setStatusFilter('all');
                }}
                className="mt-4 text-sm font-semibold text-blue-600 hover:text-blue-700"
              >
                Clear filters
              </button>
            )}
          </div>
        ) : (
          !error && (
            <>
              {/* Desktop table */}
              <div className="hidden overflow-x-auto md:block">
                <table className="w-full text-left text-sm">
                  <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
                    <tr>
                      <th className="px-6 py-4 font-semibold">Customer</th>
                      <th className="px-6 py-4 font-semibold">Role</th>
                      <th className="px-6 py-4 font-semibold">Status</th>
                      <th className="px-6 py-4 font-semibold">Registered</th>
                    </tr>
                  </thead>

                  <tbody className="divide-y divide-slate-100">
                    {filteredCustomers.map((customer) => (
                      <tr
                        key={customer.id}
                        className="transition hover:bg-slate-50"
                      >
                        <td className="px-6 py-4">
                          <div className="flex items-center gap-3">
                            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-blue-50 text-sm font-bold text-blue-700">
                              {String(customer.email || '?')
                                .charAt(0)
                                .toUpperCase()}
                            </div>

                            <div className="min-w-0">
                              <p className="truncate font-semibold text-slate-800">
                                {customer.email || 'Email unavailable'}
                              </p>
                              <p className="mt-0.5 text-xs text-slate-400">
                                Customer ID: #{customer.id}
                              </p>
                            </div>
                          </div>
                        </td>

                        <td className="px-6 py-4">
                          <RoleBadge role={customer.role} />
                        </td>

                        <td className="px-6 py-4">
                          <StatusBadge active={customer.is_active} />
                        </td>

                        <td className="px-6 py-4 text-slate-500">
                          <span className="inline-flex items-center gap-2">
                            <CalendarDays size={14} />
                            {formatDate(customer.created_at)}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Mobile cards */}
              <div className="space-y-3 p-4 md:hidden">
                {filteredCustomers.map((customer) => (
                  <div
                    key={customer.id}
                    className="rounded-xl border border-slate-200 p-4"
                  >
                    <div className="flex items-start gap-3">
                      <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-blue-50 font-bold text-blue-700">
                        {String(customer.email || '?')
                          .charAt(0)
                          .toUpperCase()}
                      </div>

                      <div className="min-w-0 flex-1">
                        <p className="break-all font-semibold text-slate-800">
                          {customer.email || 'Email unavailable'}
                        </p>
                        <p className="mt-1 text-xs text-slate-400">
                          Customer ID: #{customer.id}
                        </p>
                      </div>
                    </div>

                    <div className="mt-4 flex flex-wrap items-center justify-between gap-2 border-t border-slate-100 pt-3">
                      <RoleBadge role={customer.role} />
                      <StatusBadge active={customer.is_active} />
                    </div>

                    <div className="mt-3 flex items-center gap-2 text-xs text-slate-500">
                      <Mail size={13} />
                      Registered: {formatDate(customer.created_at)}
                    </div>
                  </div>
                ))}
              </div>
            </>
          )
        )}

        {!loading && !error && customers.length > 0 && (
          <div className="border-t border-slate-100 bg-slate-50 px-5 py-3 text-xs text-slate-500">
            Showing {filteredCustomers.length} of {customers.length} customer accounts.
          </div>
        )}
      </div>
    </section>
  );
}
