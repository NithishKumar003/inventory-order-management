import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  RefreshCw,
  ShoppingCart,
  Search,
  Package,
  ArrowRight,
  ClipboardList,
  IndianRupee,
  CalendarDays,
  AlertCircle,
  X,
  Eye,
} from 'lucide-react';
import api from '../services/api';

function formatCurrency(amount) {
  return `₹${Number(amount || 0).toLocaleString('en-IN', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

function getStatusStyle(status) {
  const styles = {
    Pending: 'bg-amber-100 text-amber-700',
    Confirmed: 'bg-green-100 text-green-700',
    Processing: 'bg-blue-100 text-blue-700',
    Shipped: 'bg-purple-100 text-purple-700',
    Delivered: 'bg-emerald-100 text-emerald-700',
    Cancelled: 'bg-red-100 text-red-700',
    Returned: 'bg-orange-100 text-orange-700',
  };

  return styles[status] || 'bg-slate-100 text-slate-600';
}

function getPaymentStyle(status) {
  const styles = {
    SUCCESS: 'bg-green-100 text-green-700',
    PENDING: 'bg-amber-100 text-amber-700',
    FAILED: 'bg-red-100 text-red-700',
  };

  return styles[status] || 'bg-slate-100 text-slate-600';
}

function getPaymentLabel(status) {
  const labels = {
    SUCCESS: 'Payment Successful',
    PENDING: 'Payment Pending',
    FAILED: 'Payment Failed',
  };

  return labels[status] || 'Payment Status Unknown';
}

function PaymentStatus({ payment }) {
  if (payment === undefined) {
    return (
      <span className="text-xs text-slate-400">
        Loading...
      </span>
    );
  }

  if (payment === null) {
    return (
      <span className="inline-flex rounded-full bg-slate-100 px-3 py-1.5 text-xs font-semibold text-slate-500">
        No payment record
      </span>
    );
  }

  if (payment.unavailable) {
    return (
      <span className="inline-flex rounded-full bg-slate-100 px-3 py-1.5 text-xs font-semibold text-slate-500">
        Status unavailable
      </span>
    );
  }

  return (
    <div className="space-y-1">
      <span
        className={`inline-flex rounded-full px-3 py-1.5 text-xs font-bold ${getPaymentStyle(payment.status)}`}
      >
        {getPaymentLabel(payment.status)}
      </span>

      {payment.transaction_reference && (
        <p className="text-xs text-slate-400">
          {payment.transaction_reference}
        </p>
      )}
    </div>
  );
}

function OrdersSkeleton() {
  return (
    <div className="space-y-3 p-5">
      {[1, 2, 3, 4].map((item) => (
        <div
          key={item}
          className="flex animate-pulse items-center gap-4 py-3"
        >
          <div className="h-10 w-10 rounded-xl bg-slate-200" />
          <div className="flex-1 space-y-2">
            <div className="h-4 w-1/3 rounded bg-slate-200" />
            <div className="h-3 w-1/4 rounded bg-slate-200" />
          </div>
          <div className="h-6 w-20 rounded-full bg-slate-200" />
        </div>
      ))}
    </div>
  );
}

export default function Orders({ isAdmin = false }) {
  const navigate = useNavigate();

  const [orders, setOrders] = useState([]);
  const [payments, setPayments] = useState({});
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  async function loadOrders() {
    setLoading(true);
    setError('');
    setPayments({});

    try {
      const endpoint = isAdmin
        ? '/orders/admin/all'
        : '/orders';

      const response = await api.get(endpoint);

      const orderList = Array.isArray(response.data)
        ? response.data
        : [];

      setOrders(orderList);

      // Fetch payment information only for the logged-in customer's orders.
      if (!isAdmin && orderList.length > 0) {
        const paymentResults = await Promise.all(
          orderList.map(async (order) => {
            try {
              const paymentResponse = await api.get(
                `/payments/order/${order.id}`
              );

              return [
                order.id,
                paymentResponse.data,
              ];
            } catch (paymentError) {
              if (paymentError.response?.status === 404) {
                return [order.id, null];
              }

              console.error(
                `Payment loading error for order ${order.id}:`,
                paymentError
              );

              return [
                order.id,
                { unavailable: true },
              ];
            }
          })
        );

        setPayments(
          Object.fromEntries(paymentResults)
        );
      }
    } catch (err) {
      console.error('Order loading error:', err);

      setError(
        err.response?.data?.detail ||
          'Unable to load orders. Please try again.'
      );

      setOrders([]);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadOrders();
  }, [isAdmin]);

  const filteredOrders = orders.filter((order) => {
    const query = search.trim().toLowerCase();

    if (!query) return true;

    return (
      String(order.order_number ?? '')
        .toLowerCase()
        .includes(query) ||
      String(order.id ?? '')
        .toLowerCase()
        .includes(query) ||
      String(order.status ?? '')
        .toLowerCase()
        .includes(query) ||
      String(order.user_id ?? '')
        .toLowerCase()
        .includes(query)
    );
  });

  const totalOrderValue = orders.reduce(
    (total, order) =>
      total + (Number(order.total_amount) || 0),
    0
  );

  const deliveredOrders = orders.filter(
    (order) => order.status === 'Delivered'
  ).length;

  const activeOrders = orders.filter(
    (order) =>
      !['Delivered', 'Cancelled', 'Returned'].includes(order.status)
  ).length;

  function formatDate(date) {
    if (!date) return '—';

    const parsedDate = new Date(date);

    if (Number.isNaN(parsedDate.getTime())) return '—';

    return parsedDate.toLocaleDateString('en-IN', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
    });
  }

  function openOrder(orderId) {
    navigate(`/orders/${orderId}`);
  }

  return (
    <section className="space-y-7">
      {/* Heading */}
      <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
        <div className="flex items-center gap-4">
          <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-blue-100 text-blue-700">
            <ClipboardList size={28} />
          </div>

          <div>
            <h1 className="text-2xl font-extrabold tracking-tight text-slate-900 sm:text-3xl">
              {isAdmin ? 'Order Management' : 'My Orders'}
            </h1>

            <p className="mt-1 text-sm text-slate-500">
              {isAdmin
                ? 'Monitor and review customer orders.'
                : 'Track your purchases, payment and order status.'}
            </p>
          </div>
        </div>

        <button
          type="button"
          onClick={loadOrders}
          disabled={loading}
          className="inline-flex items-center justify-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm font-semibold text-slate-700 transition hover:border-blue-200 hover:bg-blue-50 hover:text-blue-700 disabled:opacity-50"
        >
          <RefreshCw
            size={17}
            className={loading ? 'animate-spin' : ''}
          />
          Refresh Orders
        </button>
      </div>

      {/* Error */}
      {error && (
        <div
          role="alert"
          className="flex items-start gap-3 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700"
        >
          <AlertCircle size={19} className="mt-0.5 shrink-0" />
          <span className="flex-1">{error}</span>

          <button
            type="button"
            onClick={() => setError('')}
            aria-label="Dismiss error"
          >
            <X size={18} />
          </button>
        </div>
      )}

      {/* Summary */}
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <div className="flex items-center justify-between">
            <p className="text-sm font-medium text-slate-500">
              Total Orders
            </p>
            <div className="rounded-xl bg-blue-50 p-2.5 text-blue-600">
              <ShoppingCart size={20} />
            </div>
          </div>

          <p className="mt-4 text-3xl font-extrabold text-slate-900">
            {loading ? '—' : orders.length}
          </p>
          <p className="mt-1 text-xs text-slate-400">
            All recorded orders
          </p>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <div className="flex items-center justify-between">
            <p className="text-sm font-medium text-slate-500">
              Order Value
            </p>
            <div className="rounded-xl bg-green-50 p-2.5 text-green-600">
              <IndianRupee size={20} />
            </div>
          </div>

          <p className="mt-4 text-2xl font-extrabold text-slate-900">
            {loading ? '—' : formatCurrency(totalOrderValue)}
          </p>
          <p className="mt-1 text-xs text-slate-400">
            Combined order value
          </p>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <div className="flex items-center justify-between">
            <p className="text-sm font-medium text-slate-500">
              Active Orders
            </p>
            <div className="rounded-xl bg-amber-50 p-2.5 text-amber-600">
              <Package size={20} />
            </div>
          </div>

          <p className="mt-4 text-3xl font-extrabold text-slate-900">
            {loading ? '—' : activeOrders}
          </p>
          <p className="mt-1 text-xs text-slate-400">
            Not yet completed
          </p>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <div className="flex items-center justify-between">
            <p className="text-sm font-medium text-slate-500">
              Delivered
            </p>
            <div className="rounded-xl bg-emerald-50 p-2.5 text-emerald-600">
              <CalendarDays size={20} />
            </div>
          </div>

          <p className="mt-4 text-3xl font-extrabold text-slate-900">
            {loading ? '—' : deliveredOrders}
          </p>
          <p className="mt-1 text-xs text-slate-400">
            Successfully delivered
          </p>
        </div>
      </div>

      {/* Orders List */}
      <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
        <div className="flex flex-col justify-between gap-4 border-b border-slate-100 p-5 sm:flex-row sm:items-center">
          <div>
            <h2 className="text-lg font-bold text-slate-900">
              {isAdmin ? 'All Orders' : 'Order History'}
            </h2>
            <p className="mt-1 text-xs text-slate-500">
              {loading
                ? 'Loading orders...'
                : `${filteredOrders.length} orders displayed`}
            </p>
          </div>

          <div className="flex items-center gap-2 rounded-xl border border-slate-200 bg-slate-50 px-3">
            <Search size={18} className="text-slate-400" />

            <input
              type="search"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search orders..."
              className="w-full min-w-0 bg-transparent py-3 text-sm outline-none sm:w-64"
            />
          </div>
        </div>

        {loading ? (
          <OrdersSkeleton />
        ) : error ? (
          <div className="p-10 text-center">
            <AlertCircle
              size={36}
              className="mx-auto text-red-400"
            />

            <p className="mt-3 font-semibold text-slate-800">
              Unable to display orders
            </p>

            <button
              type="button"
              onClick={loadOrders}
              className="mt-4 rounded-xl bg-blue-600 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-blue-700"
            >
              Try Again
            </button>
          </div>
        ) : filteredOrders.length === 0 ? (
          <div className="px-5 py-16 text-center">
            <div className="mx-auto flex h-20 w-20 items-center justify-center rounded-full bg-slate-100">
              <Package size={36} className="text-slate-400" />
            </div>

            <h3 className="mt-5 text-lg font-bold text-slate-900">
              No orders found
            </h3>

            <p className="mt-2 text-sm text-slate-500">
              {search
                ? 'Try another order number, ID, or status.'
                : 'Your orders will appear here once you place an order.'}
            </p>
          </div>
        ) : (
          <>
            {/* Desktop Table */}
            <div className="hidden overflow-x-auto md:block">
              <table className="w-full text-left text-sm">
                <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
                  <tr>
                    <th className="px-5 py-4 font-semibold">
                      Order
                    </th>

                    {isAdmin && (
                      <th className="px-5 py-4 font-semibold">
                        Customer ID
                      </th>
                    )}

                    <th className="px-5 py-4 font-semibold">
                      Date
                    </th>

                    <th className="px-5 py-4 font-semibold">
                      Items
                    </th>

                    <th className="px-5 py-4 font-semibold">
                      Total
                    </th>

                    <th className="px-5 py-4 font-semibold">
                      Status
                    </th>

                    {!isAdmin && (
                      <th className="px-5 py-4 font-semibold">
                        Payment
                      </th>
                    )}

                    <th className="px-5 py-4 text-right font-semibold">
                      Action
                    </th>
                  </tr>
                </thead>

                <tbody className="divide-y divide-slate-100">
                  {filteredOrders.map((order) => (
                    <tr
                      key={order.id}
                      className="transition hover:bg-blue-50/40"
                    >
                      <td className="px-5 py-4">
                        <p className="font-bold text-slate-900">
                          {order.order_number || `Order #${order.id}`}
                        </p>
                        <p className="mt-1 text-xs text-slate-400">
                          ID: {order.id}
                        </p>
                      </td>

                      {isAdmin && (
                        <td className="px-5 py-4 text-slate-600">
                          {order.user_id ?? '—'}
                        </td>
                      )}

                      <td className="px-5 py-4 text-slate-600">
                        {formatDate(order.created_at)}
                      </td>

                      <td className="px-5 py-4 text-slate-600">
                        {Array.isArray(order.items)
                          ? order.items.length
                          : 0}
                      </td>

                      <td className="px-5 py-4 font-bold text-slate-900">
                        {formatCurrency(order.total_amount)}
                      </td>

                      <td className="px-5 py-4">
                        <span
                          className={`inline-flex rounded-full px-3 py-1.5 text-xs font-bold ${getStatusStyle(order.status)}`}
                        >
                          {order.status || 'Unknown'}
                        </span>
                      </td>

                      {!isAdmin && (
                        <td className="px-5 py-4">
                          <PaymentStatus
                            payment={payments[order.id]}
                          />
                        </td>
                      )}

                      <td className="px-5 py-4 text-right">
                        <button
                          type="button"
                          onClick={() => openOrder(order.id)}
                          className="inline-flex items-center gap-1.5 rounded-lg border border-blue-200 bg-white px-3 py-2 text-xs font-bold text-blue-700 transition hover:bg-blue-600 hover:text-white"
                        >
                          <Eye size={15} />
                          View
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Mobile Cards */}
            <div className="space-y-3 p-4 md:hidden">
              {filteredOrders.map((order) => (
                <article
                  key={order.id}
                  className="rounded-xl border border-slate-200 p-4"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="font-bold text-slate-900">
                        {order.order_number || `Order #${order.id}`}
                      </p>
                      <p className="mt-1 text-xs text-slate-500">
                        {formatDate(order.created_at)}
                      </p>
                    </div>

                    <span
                      className={`shrink-0 rounded-full px-3 py-1.5 text-xs font-bold ${getStatusStyle(order.status)}`}
                    >
                      {order.status || 'Unknown'}
                    </span>
                  </div>

                  {isAdmin && (
                    <p className="mt-3 text-xs text-slate-500">
                      Customer ID: {order.user_id ?? '—'}
                    </p>
                  )}

                  {!isAdmin && (
                    <div className="mt-3 border-t border-slate-100 pt-3">
                      <p className="mb-2 text-xs font-semibold text-slate-500">
                        Payment Status
                      </p>

                      <PaymentStatus
                        payment={payments[order.id]}
                      />
                    </div>
                  )}

                  <div className="mt-4 flex items-center justify-between border-t border-slate-100 pt-4">
                    <div>
                      <p className="text-xs text-slate-500">
                        {Array.isArray(order.items)
                          ? order.items.length
                          : 0}{' '}
                        items
                      </p>
                      <p className="mt-1 font-extrabold text-slate-900">
                        {formatCurrency(order.total_amount)}
                      </p>
                    </div>

                    <button
                      type="button"
                      onClick={() => openOrder(order.id)}
                      className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2.5 text-xs font-bold text-white transition hover:bg-blue-700"
                    >
                      View Order
                      <ArrowRight size={15} />
                    </button>
                  </div>
                </article>
              ))}
            </div>
          </>
        )}
      </div>
    </section>
  );
}