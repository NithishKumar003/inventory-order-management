
import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  ArrowLeft,
  Package,
  MapPin,
  User,
  Clock3,
  RefreshCw,
  ReceiptText,
} from 'lucide-react';

import api from '../services/api';

const formatCurrency = (amount) =>
  new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
  }).format(Number(amount || 0));

const formatDate = (value) => {
  if (!value) return '—';

  return new Date(value).toLocaleString('en-IN', {
    dateStyle: 'medium',
    timeStyle: 'short',
  });
};

export default function AdminOrderDetails() {
  const { orderId } = useParams();
  const navigate = useNavigate();

  const [order, setOrder] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  async function loadOrder() {
    setLoading(true);
    setError('');

    try {
      const response = await api.get('/orders/admin/all');

      const foundOrder = response.data.find(
        (item) => Number(item.id) === Number(orderId)
      );

      if (!foundOrder) {
        setError('Order not found.');
        return;
      }

      setOrder(foundOrder);
    } catch (err) {
      console.error('Failed to load order:', err);
      setError(
        err.response?.data?.detail ||
        'Unable to load order details.'
      );
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadOrder();
  }, [orderId]);

  if (loading) {
    return (
      <div className="flex min-h-64 items-center justify-center">
        <p className="text-sm font-medium text-slate-500">
          Loading order details...
        </p>
      </div>
    );
  }

  if (error || !order) {
    return (
      <section className="space-y-4">
        <button
          onClick={() => navigate('/orders')}
          className="inline-flex items-center gap-2 text-sm font-semibold text-blue-600"
        >
          <ArrowLeft size={17} />
          Back to Orders
        </button>

        <div className="rounded-xl border border-red-200 bg-red-50 p-5 text-sm text-red-700">
          {error || 'Order not found.'}
        </div>

        <button
          onClick={loadOrder}
          className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700"
        >
          <RefreshCw size={15} />
          Retry
        </button>
      </section>
    );
  }

  const history = [...(order.status_history || [])].sort(
    (a, b) => new Date(a.created_at) - new Date(b.created_at)
  );

  return (
    <section className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <button
            onClick={() => navigate('/orders')}
            className="mb-3 inline-flex items-center gap-2 text-sm font-semibold text-blue-600 hover:text-blue-800"
          >
            <ArrowLeft size={17} />
            Back to Orders
          </button>

          <h1 className="text-2xl font-extrabold text-slate-900">
            Order Details
          </h1>

          <p className="mt-1 text-sm text-slate-500">
            Order #{order.order_number}
          </p>
        </div>

        <span className="rounded-full bg-blue-50 px-4 py-2 text-sm font-bold text-blue-700">
          {order.status}
        </span>
      </div>

      <div className="grid gap-5 md:grid-cols-2">
        <div className="rounded-xl border border-slate-200 bg-white p-5">
          <div className="mb-4 flex items-center gap-2">
            <User size={19} className="text-blue-600" />
            <h2 className="font-bold text-slate-900">
              Customer Information
            </h2>
          </div>

          <p className="text-sm text-slate-500">Customer ID</p>
          <p className="mt-1 font-semibold text-slate-900">
            {order.user_id}
          </p>
        </div>

        <div className="rounded-xl border border-slate-200 bg-white p-5">
          <div className="mb-4 flex items-center gap-2">
            <MapPin size={19} className="text-blue-600" />
            <h2 className="font-bold text-slate-900">
              Shipping Address
            </h2>
          </div>

          <p className="text-sm leading-6 text-slate-600">
            {order.shipping_address || 'No shipping address available.'}
          </p>
        </div>
      </div>

      <div className="overflow-hidden rounded-xl border border-slate-200 bg-white">
        <div className="flex items-center gap-2 border-b border-slate-100 p-5">
          <Package size={19} className="text-blue-600" />
          <h2 className="font-bold text-slate-900">Order Items</h2>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-50 text-xs uppercase text-slate-500">
              <tr>
                <th className="px-5 py-3">Product</th>
                <th className="px-5 py-3">Quantity</th>
                <th className="px-5 py-3">Unit Price</th>
                <th className="px-5 py-3">Subtotal</th>
                <th className="px-5 py-3">Status</th>
              </tr>
            </thead>

            <tbody className="divide-y divide-slate-100">
              {(order.items || []).map((item) => (
                <tr key={item.id}>
                  <td className="px-5 py-4 font-semibold text-slate-800">
                    {item.product_name}
                    <p className="mt-1 text-xs text-slate-400">
                      Product ID: {item.product_id}
                    </p>
                  </td>

                  <td className="px-5 py-4 text-slate-600">
                    {item.quantity}
                    {item.cancelled_quantity > 0 && (
                      <p className="text-xs text-red-500">
                        Cancelled: {item.cancelled_quantity}
                      </p>
                    )}
                  </td>

                  <td className="px-5 py-4 text-slate-600">
                    {formatCurrency(item.unit_price)}
                  </td>

                  <td className="px-5 py-4 font-semibold text-slate-800">
                    {formatCurrency(item.line_subtotal)}
                  </td>

                  <td className="px-5 py-4 text-slate-600">
                    {item.status}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="grid gap-5 lg:grid-cols-2">
        <div className="rounded-xl border border-slate-200 bg-white p-5">
          <div className="mb-4 flex items-center gap-2">
            <ReceiptText size={19} className="text-blue-600" />
            <h2 className="font-bold text-slate-900">
              Payment Summary
            </h2>
          </div>

          <div className="space-y-3 text-sm">
            <div className="flex justify-between">
              <span className="text-slate-500">Subtotal</span>
              <span>{formatCurrency(order.subtotal)}</span>
            </div>

            <div className="flex justify-between">
              <span className="text-slate-500">Tax</span>
              <span>{formatCurrency(order.tax_amount)}</span>
            </div>

            <div className="flex justify-between">
              <span className="text-slate-500">
                Discount {order.coupon_code ? `(${order.coupon_code})` : ''}
              </span>
              <span className="text-green-600">
                -{formatCurrency(order.discount_amount)}
              </span>
            </div>

            <div className="flex justify-between">
              <span className="text-slate-500">Shipping</span>
              <span>{formatCurrency(order.shipping_amount)}</span>
            </div>

            <div className="flex justify-between border-t border-slate-100 pt-3 text-base font-extrabold">
              <span>Total</span>
              <span className="text-blue-700">
                {formatCurrency(order.total_amount)}
              </span>
            </div>
          </div>
        </div>

        <div className="rounded-xl border border-slate-200 bg-white p-5">
          <div className="mb-4 flex items-center gap-2">
            <Clock3 size={19} className="text-blue-600" />
            <h2 className="font-bold text-slate-900">
              Order Status History
            </h2>
          </div>

          {history.length === 0 ? (
            <p className="text-sm text-slate-500">
              No status history available.
            </p>
          ) : (
            <div className="space-y-4">
              {history.map((entry) => (
                <div
                  key={entry.id}
                  className="border-l-2 border-blue-200 pl-4"
                >
                  <p className="text-sm font-bold text-slate-800">
                    {entry.status}
                  </p>

                  {entry.note && (
                    <p className="mt-1 text-sm text-slate-500">
                      {entry.note}
                    </p>
                  )}

                  <p className="mt-1 text-xs text-slate-400">
                    {formatDate(entry.created_at)}
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </section>
  );
}