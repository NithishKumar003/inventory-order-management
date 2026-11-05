import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Truck,
  Package,
  RefreshCw,
  Search,
  MapPin,
  Clock,
  CheckCircle2,
  Circle,
  XCircle,
  AlertCircle,
  ChevronDown,
  ChevronUp,
  LoaderCircle,
} from 'lucide-react';

import api from '../services/api';

const STATUSES = [
  'Pending',
  'Confirmed',
  'Processing',
  'Shipped',
  'Delivered',
  'Cancelled',
];

const STATUS_STYLES = {
  Pending: 'bg-amber-50 text-amber-700 ring-amber-200',
  Confirmed: 'bg-blue-50 text-blue-700 ring-blue-200',
  Processing: 'bg-violet-50 text-violet-700 ring-violet-200',
  Shipped: 'bg-indigo-50 text-indigo-700 ring-indigo-200',
  Delivered: 'bg-emerald-50 text-emerald-700 ring-emerald-200',
  Cancelled: 'bg-rose-50 text-rose-700 ring-rose-200',
};

function StatusBadge({ status }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-3 py-1 text-xs font-semibold ring-1 ring-inset ${
        STATUS_STYLES[status] || 'bg-gray-100 text-gray-700 ring-gray-200'
      }`}
    >
      {status || 'Unknown'}
    </span>
  );
}

function formatDate(value) {
  if (!value) return 'Date unavailable';

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) return 'Date unavailable';

  return date.toLocaleString('en-IN', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function getProgress(status) {
  const progress = {
    Pending: 0,
    Confirmed: 1,
    Processing: 2,
    Shipped: 3,
    Delivered: 4,
  };

  return progress[status] ?? -1;
}

function TrackingTimeline({ history = [], currentStatus }) {
  const progress = getProgress(currentStatus);

  if (currentStatus === 'Cancelled') {
    return (
      <div className="rounded-xl border border-rose-100 bg-rose-50 p-4">
        <div className="flex items-center gap-2 text-sm font-semibold text-rose-700">
          <XCircle size={18} />
          This order has been cancelled.
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {STATUSES.filter((status) => status !== 'Cancelled').map(
        (status, index) => {
          const completed = progress >= index;
          const matchingHistory = history.filter(
            (entry) => entry.status === status
          );

          return (
            <div key={status} className="flex gap-3">
              <div className="flex flex-col items-center">
                {completed ? (
                  <CheckCircle2
                    size={21}
                    className="text-emerald-500"
                  />
                ) : (
                  <Circle size={21} className="text-gray-300" />
                )}

                {index !== 4 && (
                  <div
                    className={`mt-1 h-7 w-0.5 ${
                      completed && progress > index
                        ? 'bg-emerald-300'
                        : 'bg-gray-200'
                    }`}
                  />
                )}
              </div>

              <div className="min-w-0 flex-1 pb-3">
                <p
                  className={`text-sm font-semibold ${
                    completed ? 'text-gray-900' : 'text-gray-400'
                  }`}
                >
                  {status}
                </p>

                {matchingHistory.length > 0 ? (
                  matchingHistory.map((entry) => (
                    <div key={entry.id} className="mt-1">
                      <p className="text-xs text-gray-500">
                        {formatDate(entry.created_at)}
                      </p>
                      {entry.note && (
                        <p className="mt-1 text-sm text-gray-600">
                          {entry.note}
                        </p>
                      )}
                    </div>
                  ))
                ) : completed ? (
                  <p className="mt-1 text-xs text-gray-400">
                    Status reached
                  </p>
                ) : null}
              </div>
            </div>
          );
        }
      )}
    </div>
  );
}

export default function Deliveries() {
  const [orders, setOrders] = useState([]);
  const [tracking, setTracking] = useState({});
  const [expandedOrder, setExpandedOrder] = useState(null);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('All');
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState('');
  const [statusUpdates, setStatusUpdates] = useState({});
  const [notes, setNotes] = useState({});
  const [updatingOrder, setUpdatingOrder] = useState(null);
  const [successMessage, setSuccessMessage] = useState('');

  const fetchOrders = useCallback(async (showRefresh = false) => {
    if (showRefresh) {
      setRefreshing(true);
    } else {
      setLoading(true);
    }

    setError('');

    try {
      const response = await api.get('/orders/admin/all');
      setOrders(Array.isArray(response.data) ? response.data : []);
    } catch (err) {
      console.error('Failed to load delivery orders:', err);
      setError(
        err.response?.data?.detail ||
          'Unable to load delivery information. Please try again.'
      );
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    fetchOrders();
  }, [fetchOrders]);

  const filteredOrders = useMemo(() => {
    return orders.filter((order) => {
      const searchText = search.trim().toLowerCase();

      const matchesSearch =
        !searchText ||
        String(order.order_number || '').toLowerCase().includes(searchText) ||
        String(order.id || '').includes(searchText) ||
        String(order.user_id || '').includes(searchText) ||
        String(order.shipping_address || '').toLowerCase().includes(searchText);

      const matchesStatus =
        statusFilter === 'All' || order.status === statusFilter;

      return matchesSearch && matchesStatus;
    });
  }, [orders, search, statusFilter]);

  const summary = useMemo(() => ({
    total: orders.length,
    pending: orders.filter((order) =>
      ['Pending', 'Confirmed'].includes(order.status)
    ).length,
    inTransit: orders.filter((order) =>
      ['Processing', 'Shipped'].includes(order.status)
    ).length,
    delivered: orders.filter((order) => order.status === 'Delivered').length,
  }), [orders]);

  async function loadTracking(orderId) {
    if (tracking[orderId]) {
      setExpandedOrder(expandedOrder === orderId ? null : orderId);
      return;
    }

    setExpandedOrder(orderId);

    try {
      const response = await api.get(`/orders/${orderId}/tracking`);

      setTracking((previous) => ({
        ...previous,
        [orderId]: Array.isArray(response.data) ? response.data : [],
      }));
    } catch (err) {
      console.error('Failed to load tracking history:', err);
      setTracking((previous) => ({
        ...previous,
        [orderId]: [],
      }));
    }
  }

  async function updateStatus(orderId) {
    const newStatus = statusUpdates[orderId];

    if (!newStatus) {
      setError('Please select a status before updating.');
      return;
    }

    const note = (notes[orderId] || '').trim();

    if (note.length > 0 && note.length < 3) {
      setError('Tracking note must contain at least 3 characters.');
      return;
    }

    setUpdatingOrder(orderId);
    setError('');
    setSuccessMessage('');

    try {
      await api.patch(`/orders/${orderId}/status`, {
        status: newStatus,
        note: note || null,
      });

      setSuccessMessage(`Order ${orderId} status updated successfully.`);

      setStatusUpdates((previous) => ({
        ...previous,
        [orderId]: '',
      }));

      setNotes((previous) => ({
        ...previous,
        [orderId]: '',
      }));

      setTracking((previous) => {
        const updated = { ...previous };
        delete updated[orderId];
        return updated;
      });

      await fetchOrders(true);

      if (expandedOrder === orderId) {
        try {
          const response = await api.get(`/orders/${orderId}/tracking`);
          setTracking((previous) => ({
            ...previous,
            [orderId]: Array.isArray(response.data) ? response.data : [],
          }));
        } catch (trackingError) {
          console.error('Failed to refresh tracking:', trackingError);
        }
      }
    } catch (err) {
      console.error('Failed to update order status:', err);
      setError(
        err.response?.data?.detail ||
          'Unable to update order status. Please try again.'
      );
    } finally {
      setUpdatingOrder(null);
    }
  }

  return (
    <div className="space-y-6 pb-8">
      <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
        <div>
          <div className="flex items-center gap-3">
            <div className="rounded-2xl bg-indigo-100 p-3 text-indigo-700">
              <Truck size={25} />
            </div>
            <div>
              <h1 className="text-2xl font-bold tracking-tight text-gray-900">
                Deliveries
              </h1>
              <p className="mt-1 text-sm text-gray-500">
                Monitor shipments and update order progress.
              </p>
            </div>
          </div>
        </div>

        <button
          type="button"
          onClick={() => fetchOrders(true)}
          disabled={refreshing}
          className="inline-flex items-center justify-center gap-2 rounded-xl border border-gray-200 bg-white px-4 py-2.5 text-sm font-semibold text-gray-700 shadow-sm transition hover:bg-gray-50 disabled:opacity-60"
        >
          <RefreshCw
            size={16}
            className={refreshing ? 'animate-spin' : ''}
          />
          Refresh
        </button>
      </div>

      {error && (
        <div className="flex items-start gap-2 rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">
          <AlertCircle size={18} className="mt-0.5 shrink-0" />
          <p>{error}</p>
        </div>
      )}

      {successMessage && (
        <div className="flex items-center gap-2 rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-700">
          <CheckCircle2 size={18} />
          {successMessage}
        </div>
      )}

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {[
          {
            label: 'Total Orders',
            value: summary.total,
            icon: Package,
            color: 'text-blue-600 bg-blue-50',
          },
          {
            label: 'Awaiting Progress',
            value: summary.pending,
            icon: Clock,
            color: 'text-amber-600 bg-amber-50',
          },
          {
            label: 'In Progress',
            value: summary.inTransit,
            icon: Truck,
            color: 'text-indigo-600 bg-indigo-50',
          },
          {
            label: 'Delivered',
            value: summary.delivered,
            icon: CheckCircle2,
            color: 'text-emerald-600 bg-emerald-50',
          },
        ].map((item) => {
          const Icon = item.icon;

          return (
            <div
              key={item.label}
              className="rounded-2xl border border-gray-100 bg-white p-5 shadow-sm"
            >
              <div className="flex items-center justify-between">
                <p className="text-sm font-medium text-gray-500">
                  {item.label}
                </p>
                <div className={`rounded-xl p-2.5 ${item.color}`}>
                  <Icon size={19} />
                </div>
              </div>
              <p className="mt-3 text-3xl font-bold text-gray-900">
                {loading ? '—' : item.value}
              </p>
            </div>
          );
        })}
      </div>

      <div className="flex flex-col gap-3 rounded-2xl border border-gray-100 bg-white p-4 shadow-sm sm:flex-row">
        <div className="relative flex-1">
          <Search
            size={18}
            className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400"
          />
          <input
            type="search"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Search order number, customer ID or address..."
            className="w-full rounded-xl border border-gray-200 py-2.5 pl-10 pr-4 text-sm outline-none transition focus:border-indigo-400 focus:ring-2 focus:ring-indigo-100"
          />
        </div>

        <select
          value={statusFilter}
          onChange={(event) => setStatusFilter(event.target.value)}
          className="rounded-xl border border-gray-200 bg-white px-4 py-2.5 text-sm outline-none focus:border-indigo-400"
        >
          <option value="All">All statuses</option>
          {STATUSES.map((status) => (
            <option key={status} value={status}>
              {status}
            </option>
          ))}
        </select>
      </div>

      <div className="overflow-hidden rounded-2xl border border-gray-100 bg-white shadow-sm">
        <div className="flex items-center justify-between border-b border-gray-100 px-5 py-4">
          <div>
            <h2 className="font-bold text-gray-900">Delivery Orders</h2>
            <p className="mt-1 text-xs text-gray-500">
              {filteredOrders.length} order(s) found
            </p>
          </div>
        </div>

        {loading ? (
          <div className="space-y-4 p-5">
            {[1, 2, 3].map((item) => (
              <div key={item} className="animate-pulse space-y-3">
                <div className="h-5 w-1/3 rounded bg-gray-100" />
                <div className="h-4 w-2/3 rounded bg-gray-100" />
                <div className="h-12 rounded-xl bg-gray-100" />
              </div>
            ))}
          </div>
        ) : filteredOrders.length === 0 ? (
          <div className="px-5 py-16 text-center">
            <Package size={36} className="mx-auto text-gray-300" />
            <h3 className="mt-3 font-semibold text-gray-800">
              No orders found
            </h3>
            <p className="mt-1 text-sm text-gray-500">
              Try changing your search or status filter.
            </p>
          </div>
        ) : (
          <div className="divide-y divide-gray-100">
            {filteredOrders.map((order) => {
              const isExpanded = expandedOrder === order.id;

              return (
                <div key={order.id} className="p-5">
                  <div className="flex flex-col justify-between gap-4 lg:flex-row lg:items-center">
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-3">
                        <p className="font-bold text-gray-900">
                          {order.order_number || `Order #${order.id}`}
                        </p>
                        <StatusBadge status={order.status} />
                      </div>

                      <p className="mt-2 text-xs text-gray-500">
                        Order ID: {order.id} · Customer ID: {order.user_id}
                      </p>

                      <div className="mt-3 flex items-start gap-2 text-sm text-gray-600">
                        <MapPin
                          size={16}
                          className="mt-0.5 shrink-0 text-gray-400"
                        />
                        <span className="break-words">
                          {order.shipping_address || 'No shipping address provided'}
                        </span>
                      </div>
                    </div>

                    <div className="flex flex-wrap items-center gap-2">
                      <button
                        type="button"
                        onClick={() => loadTracking(order.id)}
                        className="inline-flex items-center gap-2 rounded-xl border border-gray-200 px-3 py-2.5 text-sm font-semibold text-gray-700 transition hover:bg-gray-50"
                      >
                        <Clock size={16} />
                        Tracking
                        {isExpanded ? (
                          <ChevronUp size={16} />
                        ) : (
                          <ChevronDown size={16} />
                        )}
                      </button>
                    </div>
                  </div>

                  {isExpanded && (
                    <div className="mt-5 grid gap-5 border-t border-gray-100 pt-5 lg:grid-cols-2">
                      <div className="rounded-xl bg-gray-50 p-4">
                        <h3 className="mb-4 font-semibold text-gray-900">
                          Tracking History
                        </h3>
                        {tracking[order.id] ? (
                          tracking[order.id].length > 0 ? (
                            <TrackingTimeline
                              history={tracking[order.id]}
                              currentStatus={order.status}
                            />
                          ) : (
                            <p className="text-sm text-gray-500">
                              No tracking history is available yet.
                            </p>
                          )
                        ) : (
                          <div className="flex items-center gap-2 text-sm text-gray-500">
                            <LoaderCircle size={17} className="animate-spin" />
                            Loading tracking history...
                          </div>
                        )}
                      </div>

                      <div className="rounded-xl border border-gray-100 p-4">
                        <h3 className="font-semibold text-gray-900">
                          Update Delivery Status
                        </h3>
                        <p className="mt-1 text-xs text-gray-500">
                          Update the order status and add an optional tracking note.
                        </p>

                        <label className="mt-4 block text-xs font-semibold text-gray-600">
                          New status
                        </label>
                        <select
                          value={statusUpdates[order.id] || ''}
                          onChange={(event) =>
                            setStatusUpdates((previous) => ({
                              ...previous,
                              [order.id]: event.target.value,
                            }))
                          }
                          className="mt-1 w-full rounded-xl border border-gray-200 bg-white px-3 py-2.5 text-sm outline-none focus:border-indigo-400"
                        >
                          <option value="">Select status</option>
                          {STATUSES.filter(
                            (status) => status !== order.status
                          ).map((status) => (
                            <option key={status} value={status}>
                              {status}
                            </option>
                          ))}
                        </select>

                        <label className="mt-4 block text-xs font-semibold text-gray-600">
                          Tracking note (optional)
                        </label>
                        <textarea
                          rows={3}
                          maxLength={300}
                          value={notes[order.id] || ''}
                          onChange={(event) =>
                            setNotes((previous) => ({
                              ...previous,
                              [order.id]: event.target.value,
                            }))
                          }
                          placeholder="Example: Package dispatched from warehouse..."
                          className="mt-1 w-full resize-y rounded-xl border border-gray-200 px-3 py-2.5 text-sm outline-none focus:border-indigo-400"
                        />

                        <button
                          type="button"
                          onClick={() => updateStatus(order.id)}
                          disabled={updatingOrder === order.id}
                          className="mt-3 inline-flex w-full items-center justify-center gap-2 rounded-xl bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-60"
                        >
                          {updatingOrder === order.id ? (
                            <>
                              <LoaderCircle size={16} className="animate-spin" />
                              Updating...
                            </>
                          ) : (
                            <>
                              <CheckCircle2 size={16} />
                              Update Status
                            </>
                          )}
                        </button>
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