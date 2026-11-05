
import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  RefreshCw,
  Search,
  RotateCcw,
  CheckCircle2,
  XCircle,
  Clock3,
  IndianRupee,
  Package,
  AlertCircle,
  LoaderCircle,
  MessageSquare,
  CreditCard,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import api from '../services/api';

const formatCurrency = (value) =>
  new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 2,
  }).format(Number(value || 0));

const formatDate = (value) => {
  if (!value) return '—';
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? '—'
    : date.toLocaleString('en-IN', {
        dateStyle: 'medium',
        timeStyle: 'short',
      });
};

const statusStyles = {
  PENDING: 'bg-amber-50 text-amber-700 ring-amber-200',
  APPROVED: 'bg-blue-50 text-blue-700 ring-blue-200',
  REJECTED: 'bg-rose-50 text-rose-700 ring-rose-200',
  COMPLETED: 'bg-emerald-50 text-emerald-700 ring-emerald-200',
};

const refundStyles = {
  NOT_STARTED: 'bg-slate-100 text-slate-600',
  PENDING: 'bg-amber-50 text-amber-700',
  SUCCEEDED: 'bg-emerald-50 text-emerald-700',
  FAILED: 'bg-rose-50 text-rose-700',
};

function StatusBadge({ status }) {
  const value = status || 'UNKNOWN';

  return (
    <span
      className={`inline-flex rounded-full px-3 py-1 text-xs font-bold ring-1 ring-inset ${
        statusStyles[value] || 'bg-slate-100 text-slate-600 ring-slate-200'
      }`}
    >
      {value.replaceAll('_', ' ')}
    </span>
  );
}

function RefundBadge({ status }) {
  const value = status || 'NOT STARTED';

  return (
    <span
      className={`inline-flex rounded-full px-3 py-1 text-xs font-bold ${
        refundStyles[status] || 'bg-slate-100 text-slate-600'
      }`}
    >
      {value.replaceAll('_', ' ')}
    </span>
  );
}

function StatCard({ title, value, description, icon: Icon, color }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-medium text-slate-500">{title}</p>
          <p className="mt-2 text-2xl font-bold text-slate-900">{value}</p>
          <p className="mt-1 text-xs text-slate-500">{description}</p>
        </div>
        <div className={`rounded-xl p-3 ${color}`}>
          <Icon size={22} />
        </div>
      </div>
    </div>
  );
}

function LoadingCard() {
  return (
    <div className="animate-pulse rounded-2xl border border-slate-200 bg-white p-5">
      <div className="h-3 w-24 rounded bg-slate-200" />
      <div className="mt-4 h-7 w-16 rounded bg-slate-200" />
      <div className="mt-3 h-3 w-32 rounded bg-slate-100" />
    </div>
  );
}

export default function Returns() {
  const [returns, setReturns] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [expandedId, setExpandedId] = useState(null);
  const [notes, setNotes] = useState({});
  const [actionLoading, setActionLoading] = useState({});

  const fetchReturns = useCallback(async (showRefresh = false) => {
    if (showRefresh) {
      setRefreshing(true);
    } else {
      setLoading(true);
    }

    setError('');

    try {
      const response = await api.get('/returns/admin');
      setReturns(Array.isArray(response.data) ? response.data : []);
    } catch (err) {
      setError(
        err.response?.data?.detail ||
          'Unable to load return requests. Please try again.'
      );
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    fetchReturns();
  }, [fetchReturns]);

  const filteredReturns = useMemo(() => {
    const term = search.trim().toLowerCase();

    return returns.filter((item) => {
      const matchesSearch =
        !term ||
        [
          item.id,
          item.order_id,
          item.order_item_id,
          item.product_id,
          item.user_id,
          item.reason,
          item.status,
          item.refund_status,
        ].some((value) => String(value ?? '').toLowerCase().includes(term));

      const matchesStatus =
        statusFilter === 'ALL' || item.status === statusFilter;

      return matchesSearch && matchesStatus;
    });
  }, [returns, search, statusFilter]);

  const stats = useMemo(() => {
    const total = returns.length;
    const pending = returns.filter((item) => item.status === 'PENDING').length;
    const approved = returns.filter((item) => item.status === 'APPROVED').length;
    const completed = returns.filter((item) => item.status === 'COMPLETED').length;
    const refundTotal = returns
      .filter((item) => item.status === 'COMPLETED')
      .reduce((sum, item) => sum + Number(item.refund_amount || 0), 0);

    return { total, pending, approved, completed, refundTotal };
  }, [returns]);

  const runAction = async (returnId, action, request) => {
    setActionLoading((previous) => ({
      ...previous,
      [returnId]: action,
    }));
    setError('');
    setSuccess('');

    try {
      await request();
      setSuccess(
        action === 'approve'
          ? `Return #${returnId} approved successfully.`
          : action === 'reject'
            ? `Return #${returnId} rejected successfully.`
            : `Refund completion requested for return #${returnId}.`
      );

      await fetchReturns(true);
    } catch (err) {
      setError(
        err.response?.data?.detail ||
          'The action could not be completed. Please try again.'
      );
    } finally {
      setActionLoading((previous) => {
        const next = { ...previous };
        delete next[returnId];
        return next;
      });
    }
  };

  const moderateReturn = (item, status) => {
    const adminNote = (notes[item.id] || '').trim();

    runAction(item.id, status === 'APPROVED' ? 'approve' : 'reject', () =>
      api.patch(`/returns/admin/${item.id}/moderation`, {
        status,
        admin_note: adminNote || null,
      })
    );
  };

  const completeReturn = (item) => {
    const confirmed = window.confirm(
      `Process the refund for return #${item.id}? This will contact the Payment Service.`
    );

    if (!confirmed) return;

    runAction(item.id, 'complete', () =>
      api.post(`/returns/admin/${item.id}/complete`)
    );
  };

  const toggleExpanded = (id) => {
    setExpandedId((current) => (current === id ? null : id));
  };

  return (
    <div className="min-h-screen space-y-6 bg-slate-50/50 p-4 sm:p-6 lg:p-8">
      <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
        <div>
          <div className="flex items-center gap-2 text-sm font-semibold text-indigo-600">
            <RotateCcw size={16} />
            Order management
          </div>
          <h1 className="mt-2 text-2xl font-bold tracking-tight text-slate-900 sm:text-3xl">
            Returns Management
          </h1>
          <p className="mt-1 text-sm text-slate-500">
            Review return requests and monitor refund processing.
          </p>
        </div>

        <button
          onClick={() => fetchReturns(true)}
          disabled={refreshing || loading}
          className="inline-flex items-center justify-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-semibold text-slate-700 shadow-sm transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60"
        >
          <RefreshCw
            size={16}
            className={refreshing ? 'animate-spin' : ''}
          />
          Refresh
        </button>
      </div>

      {error && (
        <div className="flex items-start gap-3 rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">
          <AlertCircle size={19} className="mt-0.5 shrink-0" />
          <p>{error}</p>
        </div>
      )}

      {success && (
        <div className="flex items-start gap-3 rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-700">
          <CheckCircle2 size={19} className="mt-0.5 shrink-0" />
          <p>{success}</p>
        </div>
      )}

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {loading ? (
          <>
            <LoadingCard />
            <LoadingCard />
            <LoadingCard />
            <LoadingCard />
          </>
        ) : (
          <>
            <StatCard
              title="Total Requests"
              value={stats.total}
              description="All return requests"
              icon={Package}
              color="bg-indigo-50 text-indigo-600"
            />
            <StatCard
              title="Pending Review"
              value={stats.pending}
              description="Waiting for admin action"
              icon={Clock3}
              color="bg-amber-50 text-amber-600"
            />
            <StatCard
              title="Approved Returns"
              value={stats.approved}
              description="Waiting for refund completion"
              icon={CheckCircle2}
              color="bg-blue-50 text-blue-600"
            />
            <StatCard
              title="Completed Refunds"
              value={formatCurrency(stats.refundTotal)}
              description={`${stats.completed} completed returns`}
              icon={IndianRupee}
              color="bg-emerald-50 text-emerald-600"
            />
          </>
        )}
      </div>

      <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:p-5">
        <div className="flex flex-col gap-3 lg:flex-row">
          <div className="relative flex-1">
            <Search
              size={18}
              className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"
            />
            <input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search return, order, product, customer or reason..."
              className="w-full rounded-xl border border-slate-200 bg-slate-50 py-3 pl-10 pr-4 text-sm outline-none transition focus:border-indigo-400 focus:bg-white focus:ring-4 focus:ring-indigo-50"
            />
          </div>

          <select
            value={statusFilter}
            onChange={(event) => setStatusFilter(event.target.value)}
            className="rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm font-medium text-slate-700 outline-none focus:border-indigo-400 focus:ring-4 focus:ring-indigo-50"
          >
            <option value="ALL">All statuses</option>
            <option value="PENDING">Pending</option>
            <option value="APPROVED">Approved</option>
            <option value="REJECTED">Rejected</option>
            <option value="COMPLETED">Completed</option>
          </select>
        </div>
      </div>

      <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
        <div className="flex items-center justify-between border-b border-slate-100 px-5 py-4">
          <div>
            <h2 className="font-bold text-slate-900">Return requests</h2>
            <p className="mt-1 text-xs text-slate-500">
              {filteredReturns.length} request(s) shown
            </p>
          </div>
          <span className="rounded-lg bg-slate-100 px-3 py-1.5 text-xs font-semibold text-slate-600">
            Admin view
          </span>
        </div>

        {loading ? (
          <div className="space-y-3 p-5">
            {[1, 2, 3, 4].map((item) => (
              <div
                key={item}
                className="h-24 animate-pulse rounded-xl bg-slate-100"
              />
            ))}
          </div>
        ) : filteredReturns.length === 0 ? (
          <div className="px-5 py-16 text-center">
            <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-slate-100 text-slate-400">
              <RotateCcw size={25} />
            </div>
            <h3 className="mt-4 font-bold text-slate-800">
              No return requests found
            </h3>
            <p className="mt-1 text-sm text-slate-500">
              Try changing the search or status filter.
            </p>
          </div>
        ) : (
          <div className="divide-y divide-slate-100">
            {filteredReturns.map((item) => {
              const expanded = expandedId === item.id;
              const busy = actionLoading[item.id];

              return (
                <div key={item.id} className="p-4 sm:p-5">
                  <div className="flex flex-col justify-between gap-4 xl:flex-row xl:items-center">
                    <div className="flex min-w-0 items-start gap-3">
                      <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-indigo-50 text-indigo-600">
                        <RotateCcw size={20} />
                      </div>

                      <div className="min-w-0">
                        <div className="flex flex-wrap items-center gap-2">
                          <h3 className="font-bold text-slate-900">
                            Return #{item.id}
                          </h3>
                          <StatusBadge status={item.status} />
                        </div>

                        <p className="mt-1 text-sm text-slate-500">
                          Order #{item.order_id} · Customer #{item.user_id}
                        </p>

                        <p className="mt-1 text-xs text-slate-400">
                          Requested {formatDate(item.created_at)}
                        </p>
                      </div>
                    </div>

                    <div className="grid grid-cols-2 gap-4 sm:grid-cols-4 xl:min-w-[560px]">
                      <div>
                        <p className="text-xs text-slate-400">Product ID</p>
                        <p className="mt-1 font-semibold text-slate-800">
                          #{item.product_id}
                        </p>
                      </div>
                      <div>
                        <p className="text-xs text-slate-400">Quantity</p>
                        <p className="mt-1 font-semibold text-slate-800">
                          {item.quantity}
                        </p>
                      </div>
                      <div>
                        <p className="text-xs text-slate-400">Refund amount</p>
                        <p className="mt-1 font-bold text-slate-900">
                          {formatCurrency(item.refund_amount)}
                        </p>
                      </div>
                      <div>
                        <p className="text-xs text-slate-400">Refund status</p>
                        <div className="mt-1">
                          <RefundBadge status={item.refund_status} />
                        </div>
                      </div>
                    </div>

                    <button
                      onClick={() => toggleExpanded(item.id)}
                      className="inline-flex shrink-0 items-center justify-center gap-2 rounded-xl border border-slate-200 px-4 py-2.5 text-sm font-semibold text-slate-700 transition hover:bg-slate-50"
                    >
                      {expanded ? 'Hide details' : 'View details'}
                      {expanded ? (
                        <ChevronUp size={16} />
                      ) : (
                        <ChevronDown size={16} />
                      )}
                    </button>
                  </div>

                  {expanded && (
                    <div className="mt-5 grid gap-5 rounded-xl bg-slate-50 p-4 lg:grid-cols-2 sm:p-5">
                      <div className="space-y-4">
                        <div>
                          <p className="text-xs font-bold uppercase tracking-wide text-slate-400">
                            Return reason
                          </p>
                          <p className="mt-2 text-sm leading-6 text-slate-700">
                            {item.reason}
                          </p>
                        </div>

                        <div>
                          <p className="text-xs font-bold uppercase tracking-wide text-slate-400">
                            Refund information
                          </p>
                          <div className="mt-2 space-y-2 text-sm">
                            <p className="flex items-center gap-2 text-slate-700">
                              <IndianRupee size={15} />
                              Amount: {formatCurrency(item.refund_amount)}
                            </p>
                            <p className="flex items-center gap-2 text-slate-700">
                              <CreditCard size={15} />
                              Payment refund ID:{' '}
                              {item.payment_refund_id ?? 'Not created'}
                            </p>
                            <p className="text-slate-700">
                              Refund status:{' '}
                              <RefundBadge status={item.refund_status} />
                            </p>
                          </div>
                        </div>

                        {item.refund_failure_reason && (
                          <div className="rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700">
                            <strong>Refund failure:</strong>{' '}
                            {item.refund_failure_reason}
                          </div>
                        )}

                        {item.admin_note && (
                          <div className="rounded-lg border border-slate-200 bg-white p-3">
                            <p className="flex items-center gap-2 text-xs font-bold uppercase tracking-wide text-slate-400">
                              <MessageSquare size={14} />
                              Admin note
                            </p>
                            <p className="mt-2 text-sm text-slate-700">
                              {item.admin_note}
                            </p>
                          </div>
                        )}
                      </div>

                      <div className="space-y-4">
                        {item.status === 'PENDING' && (
                          <div>
                            <label className="mb-2 block text-sm font-semibold text-slate-700">
                              Admin note (optional)
                            </label>
                            <textarea
                              rows={3}
                              maxLength={500}
                              value={notes[item.id] || ''}
                              onChange={(event) =>
                                setNotes((previous) => ({
                                  ...previous,
                                  [item.id]: event.target.value,
                                }))
                              }
                              placeholder="Add a reason or note for this decision..."
                              className="w-full resize-y rounded-xl border border-slate-200 bg-white p-3 text-sm outline-none focus:border-indigo-400 focus:ring-4 focus:ring-indigo-50"
                            />
                            <p className="mt-1 text-right text-xs text-slate-400">
                              {(notes[item.id] || '').length}/500
                            </p>

                            <div className="mt-3 flex flex-wrap gap-2">
                              <button
                                onClick={() => moderateReturn(item, 'APPROVED')}
                                disabled={Boolean(busy)}
                                className="inline-flex items-center gap-2 rounded-xl bg-emerald-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-emerald-700 disabled:opacity-50"
                              >
                                {busy === 'approve' ? (
                                  <LoaderCircle size={16} className="animate-spin" />
                                ) : (
                                  <CheckCircle2 size={16} />
                                )}
                                Approve
                              </button>

                              <button
                                onClick={() => moderateReturn(item, 'REJECTED')}
                                disabled={Boolean(busy)}
                                className="inline-flex items-center gap-2 rounded-xl bg-rose-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-rose-700 disabled:opacity-50"
                              >
                                {busy === 'reject' ? (
                                  <LoaderCircle size={16} className="animate-spin" />
                                ) : (
                                  <XCircle size={16} />
                                )}
                                Reject
                              </button>
                            </div>
                          </div>
                        )}

                        {item.status === 'APPROVED' && (
                          <div className="rounded-xl border border-blue-200 bg-blue-50 p-4">
                            <p className="text-sm font-semibold text-blue-800">
                              This return is approved.
                            </p>
                            <p className="mt-1 text-xs leading-5 text-blue-700">
                              Completing it will contact the Payment Service to
                              process the refund.
                            </p>
                            <button
                              onClick={() => completeReturn(item)}
                              disabled={Boolean(busy)}
                              className="mt-4 inline-flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-blue-700 disabled:opacity-50"
                            >
                              {busy === 'complete' ? (
                                <LoaderCircle size={16} className="animate-spin" />
                              ) : (
                                <IndianRupee size={16} />
                              )}
                              Process refund
                            </button>
                          </div>
                        )}

                        {item.status === 'COMPLETED' && (
                          <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-800">
                            <CheckCircle2 size={20} className="mb-2" />
                            Return completed. Refund status is shown on the
                            left.
                          </div>
                        )}

                        {item.status === 'REJECTED' && (
                          <div className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800">
                            <XCircle size={20} className="mb-2" />
                            This return request was rejected.
                          </div>
                        )}

                        <div className="border-t border-slate-200 pt-3 text-xs text-slate-500">
                          <p>Order item ID: #{item.order_item_id}</p>
                          <p className="mt-1">Idempotency key: {item.idempotency_key}</p>
                          <p className="mt-1">Last updated: {formatDate(item.updated_at)}</p>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
