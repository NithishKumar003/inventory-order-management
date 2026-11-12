
import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  LayoutDashboard,
  Package,
  Boxes,
  ShoppingCart,
  BarChart3,
  RefreshCw,
  AlertTriangle,
  TrendingDown,
  Clock,
  ArrowRight,
  CheckCircle2,
  XCircle,
  PackageCheck,
} from 'lucide-react';
import api from './services/api';

function formatDate(value) {
  if (!value) return '—';

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) return '—';

  return date.toLocaleString('en-IN', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function formatCurrency(value) {
  if (value == null || Number.isNaN(Number(value))) return '—';

  return `₹${Number(value).toLocaleString('en-IN', {
    maximumFractionDigits: 2,
  })}`;
}

function StatusBadge({ status }) {
  const value = String(status || 'Unknown').toLowerCase();

  let styles = 'bg-slate-100 text-slate-600';

  if (['delivered', 'completed', 'paid'].includes(value)) {
    styles = 'bg-emerald-50 text-emerald-700';
  } else if (['cancelled', 'failed', 'returned'].includes(value)) {
    styles = 'bg-red-50 text-red-700';
  } else if (
    ['pending', 'processing', 'confirmed', 'shipped'].includes(value)
  ) {
    styles = 'bg-amber-50 text-amber-700';
  }

  return (
    <span className={`inline-flex rounded-full px-3 py-1.5 text-xs font-semibold capitalize ${styles}`}>
      {status || 'Unknown'}
    </span>
  );
}

function StatCard({ title, value, note, icon: Icon, color, loading }) {
  const colors = {
    blue: 'bg-blue-50 text-blue-600',
    green: 'bg-emerald-50 text-emerald-600',
    amber: 'bg-amber-50 text-amber-600',
    violet: 'bg-violet-50 text-violet-600',
  };

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition duration-200 hover:-translate-y-1 hover:shadow-md">
      <div className="flex items-center justify-between gap-3">
        <p className="text-sm font-medium text-slate-500">{title}</p>
        <div className={`rounded-xl p-3 ${colors[color]}`}>
          <Icon size={21} />
        </div>
      </div>

      <div className="mt-4">
        {loading ? (
          <div className="h-9 w-24 animate-pulse rounded-lg bg-slate-100" />
        ) : (
          <p className="break-words text-3xl font-bold tracking-tight text-slate-900">
            {value}
          </p>
        )}
      </div>

      <p className="mt-2 text-xs text-slate-400">{note}</p>
    </div>
  );
}

function SectionHeading({ title, description, link, linkText }) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 p-5 md:p-6">
      <div>
        <h2 className="text-lg font-bold text-slate-900">{title}</h2>
        <p className="mt-1 text-sm text-slate-500">{description}</p>
      </div>

      {link && (
        <Link
          to={link}
          className="inline-flex items-center gap-1.5 text-sm font-semibold text-blue-600 transition hover:text-blue-800"
        >
          {linkText || 'View all'}
          <ArrowRight size={15} />
        </Link>
      )}
    </div>
  );
}

function SkeletonRows() {
  return (
    <div className="space-y-3 p-5">
      {[1, 2, 3, 4].map((item) => (
        <div
          key={item}
          className="h-12 animate-pulse rounded-xl bg-slate-100"
        />
      ))}
    </div>
  );
}

function App() {
  const [products, setProducts] = useState([]);
  const [inventory, setInventory] = useState([]);
  const [lowStock, setLowStock] = useState([]);
  const [orders, setOrders] = useState([]);

  const [coupons, setCoupons] = useState([]);
  const [couponLoading, setCouponLoading] = useState(false);
  const [couponError, setCouponError] = useState('');

  const [couponForm, setCouponForm] = useState({
    code: '',
    discount_type: 'PERCENT',
    discount_value: '',
    minimum_order_amount: '0',
    maximum_discount_amount: '',
    usage_limit: '',
    starts_at: '',
    expires_at: '',
  });

  const [couponSaving, setCouponSaving] = useState(false);
  const [couponMessage, setCouponMessage] = useState('');

  const [loading, setLoading] = useState(true);
  const [errors, setErrors] = useState([]);

  async function loadDashboard() {
    setLoading(true);

    const results = await Promise.allSettled([
      api.get('/products'),
      api.get('/inventory'),
      api.get('/inventory/low-stock'),
      api.get('/orders'),
      api.get('/coupons'),
    ]);

    const messages = [];

    if (results[0].status === 'fulfilled') {
      setProducts(
        Array.isArray(results[0].value.data)
          ? results[0].value.data
          : []
      );
    } else {
      messages.push('Products could not be loaded.');
    }

    if (results[1].status === 'fulfilled') {
      setInventory(
        Array.isArray(results[1].value.data)
          ? results[1].value.data
          : []
      );
    } else {
      messages.push('Inventory could not be loaded.');
    }

    if (results[2].status === 'fulfilled') {
      setLowStock(
        Array.isArray(results[2].value.data)
          ? results[2].value.data
          : []
      );
    } else {
      messages.push('Low-stock data could not be loaded.');
    }

    if (results[3].status === 'fulfilled') {
      setOrders(
        Array.isArray(results[3].value.data)
          ? results[3].value.data
          : []
      );
    } else {
      messages.push('Orders could not be loaded. Authentication may be required.');
    }

    if (results[4].status === 'fulfilled') {
      setCoupons(
        Array.isArray(results[4].value.data)
          ? results[4].value.data
          : []
      );
      setCouponError('');
    } else {
      setCouponError('Coupons could not be loaded.');
    }

    setErrors(messages);
    setLoading(false);
  }

  async function createCoupon(event) {
    event.preventDefault();

    if (couponSaving) return;

    setCouponSaving(true);
    setCouponError('');
    setCouponMessage('');

    try {
      const payload = {
        code: couponForm.code.trim().toUpperCase(),
        discount_type: couponForm.discount_type,
        discount_value: Number(couponForm.discount_value),
        minimum_order_amount: Number(couponForm.minimum_order_amount || 0),
        maximum_discount_amount:
          couponForm.maximum_discount_amount === ''
            ? null
            : Number(couponForm.maximum_discount_amount),
        usage_limit:
          couponForm.usage_limit === ''
            ? null
            : Number(couponForm.usage_limit),
        starts_at: couponForm.starts_at
          ? new Date(couponForm.starts_at).toISOString()
          : null,
        expires_at: couponForm.expires_at
          ? new Date(couponForm.expires_at).toISOString()
          : null,
      };

      await api.post('/coupons', payload);

      setCouponMessage('Coupon created successfully!');

      setCouponForm({
        code: '',
        discount_type: 'PERCENT',
        discount_value: '',
        minimum_order_amount: '0',
        maximum_discount_amount: '',
        usage_limit: '',
        starts_at: '',
        expires_at: '',
      });

      const response = await api.get('/coupons');
      setCoupons(Array.isArray(response.data) ? response.data : []);
    } catch (error) {
      setCouponError(
        error.response?.data?.detail || 'Unable to create coupon.'
      );
    } finally {
      setCouponSaving(false);
    }
  }

  async function toggleCouponStatus(coupon) {
    setCouponError('');
    setCouponMessage('');

    try {
      const response = await api.patch(
        `/coupons/${coupon.id}/status`,
        {
          is_active: !coupon.is_active,
        }
      );

      setCoupons((previous) =>
        previous.map((item) =>
          item.id === coupon.id ? response.data : item
        )
      );

      setCouponMessage(
        `Coupon ${coupon.code} ${
          response.data.is_active ? 'activated' : 'deactivated'
        } successfully.`
      );
    } catch (error) {
      setCouponError(
        error.response?.data?.detail ||
          'Unable to update coupon status.'
      );
    }
  }



  useEffect(() => {
    loadDashboard();
  }, []);

  const activeProducts = products.filter(
    (product) => product.is_active
  );

  const totalUnits = inventory.reduce(
    (total, item) => total + (Number(item.quantity) || 0),
    0
  );

  const orderValue = orders.reduce(
    (total, order) => total + (Number(order.total_amount) || 0),
    0
  );

  const recentOrders = useMemo(() => {
    return [...orders]
      .sort((a, b) => {
        const dateA = new Date(a.created_at || 0).getTime();
        const dateB = new Date(b.created_at || 0).getTime();

        if (!Number.isNaN(dateA) && !Number.isNaN(dateB)) {
          return dateB - dateA;
        }

        return Number(b.id || 0) - Number(a.id || 0);
      })
      .slice(0, 5);
  }, [orders]);

  const summaryCards = [
    {
      title: 'Active Products',
      value: errors.some((message) => message.startsWith('Products'))
        ? 'Unavailable'
        : activeProducts.length.toLocaleString('en-IN'),
      note: 'Active product listings',
      icon: Package,
      color: 'blue',
    },
    {
      title: 'Low Stock Items',
      value: errors.some((message) => message.startsWith('Low-stock'))
        ? 'Unavailable'
        : lowStock.length.toLocaleString('en-IN'),
      note: 'Products needing attention',
      icon: AlertTriangle,
      color: 'amber',
    },
    {
      title: 'Inventory Units',
      value: errors.some((message) => message.startsWith('Inventory'))
        ? 'Unavailable'
        : totalUnits.toLocaleString('en-IN'),
      note: 'Total recorded quantities',
      icon: Boxes,
      color: 'green',
    },
    {
      title: 'Total Orders',
      value: errors.some((message) => message.startsWith('Orders'))
        ? 'Unavailable'
        : orders.length.toLocaleString('en-IN'),
      note: 'Orders returned by Order Service',
      icon: ShoppingCart,
      color: 'violet',
    },
  ];

  const orderServiceError = errors.some(
    (message) => message.startsWith('Orders')
  );

  return (
    <section className="min-h-screen space-y-7 p-4 md:p-7">
      {/* Dashboard heading */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="mb-2 flex items-center gap-2 text-sm font-medium text-blue-600">
            <LayoutDashboard size={16} />
            Admin Workspace
          </div>

          <h1 className="text-3xl font-bold tracking-tight text-slate-900">
            Dashboard
          </h1>

          <p className="mt-2 text-sm text-slate-500">
            Monitor your products, inventory, and orders in one place.
          </p>
        </div>

        <button
          type="button"
          onClick={loadDashboard}
          disabled={loading}
          className="inline-flex items-center gap-2 rounded-xl bg-slate-900 px-5 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-50"
        >
          <RefreshCw
            size={16}
            className={loading ? 'animate-spin' : ''}
          />
          {loading ? 'Refreshing...' : 'Refresh Dashboard'}
        </button>
      </div>

      {/* Partial service errors */}
      {errors.length > 0 && (
        <div
          role="alert"
          className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800"
        >
          <div className="flex items-center gap-2 font-semibold">
            <AlertTriangle size={18} />
            Some dashboard data is unavailable
          </div>

          <ul className="mt-2 list-inside list-disc space-y-1">
            {errors.map((message) => (
              <li key={message}>{message}</li>
            ))}
          </ul>

          <p className="mt-2 text-xs text-amber-700">
            Other successfully loaded sections remain available.
          </p>
        </div>
      )}

      {/* Statistics */}
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {summaryCards.map((card) => (
          <StatCard
            key={card.title}
            {...card}
            loading={loading}
          />
        ))}
      </div>

      {/* Order overview */}
      <div className="grid gap-4 lg:grid-cols-3">
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm lg:col-span-2">
          <div className="flex items-center gap-3">
            <div className="rounded-xl bg-blue-50 p-3 text-blue-600">
              <ShoppingCart size={22} />
            </div>

            <div>
              <p className="text-sm text-slate-500">Combined order value</p>
              {loading ? (
                <div className="mt-2 h-8 w-32 animate-pulse rounded bg-slate-100" />
              ) : orderServiceError ? (
                <p className="mt-1 text-xl font-bold text-slate-400">
                  Unavailable
                </p>
              ) : (
                <p className="mt-1 text-2xl font-bold text-slate-900">
                  {formatCurrency(orderValue)}
                </p>
              )}
            </div>
          </div>

          <p className="mt-4 text-xs text-slate-400">
            Sum of total_amount for orders returned by the Order Service.
            This is not a separate payment or profit calculation.
          </p>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <div className="flex items-center gap-3">
            <div className="rounded-xl bg-amber-50 p-3 text-amber-600">
              <TrendingDown size={22} />
            </div>

            <div>
              <p className="text-sm text-slate-500">Stock attention</p>
              <p className="mt-1 text-2xl font-bold text-slate-900">
                {loading ? '—' : lowStock.length}
              </p>
            </div>
          </div>

          <Link
            to="/inventory"
            className="mt-4 inline-flex items-center gap-1.5 text-sm font-semibold text-blue-600 hover:text-blue-800"
          >
            Review inventory
            <ArrowRight size={15} />
          </Link>
        </div>
      </div>

      {/* Low stock */}
      <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
        <SectionHeading
          title="Low-stock products"
          description="Products that need stock replenishment."
          link="/inventory"
          linkText="View inventory"
        />

        {loading ? (
          <SkeletonRows />
        ) : errors.some((message) => message.startsWith('Low-stock')) ? (
          <div className="p-6 text-sm text-amber-700">
            Low-stock information is currently unavailable.
          </div>
        ) : lowStock.length === 0 ? (
          <div className="p-10 text-center">
            <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-xl bg-emerald-50 text-emerald-600">
              <CheckCircle2 size={24} />
            </div>

            <p className="mt-3 font-semibold text-slate-800">
              No low-stock items
            </p>
            <p className="mt-1 text-sm text-slate-500">
              No products were returned by the low-stock endpoint.
            </p>
          </div>
        ) : (
          <>
            <div className="hidden overflow-x-auto md:block">
              <table className="w-full text-left text-sm">
                <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
                  <tr>
                    <th className="px-6 py-4 font-semibold">Product</th>
                    <th className="px-6 py-4 font-semibold">Product ID</th>
                    <th className="px-6 py-4 font-semibold">Quantity</th>
                    <th className="px-6 py-4 font-semibold">Last updated</th>
                  </tr>
                </thead>

                <tbody className="divide-y divide-slate-100">
                  {lowStock.slice(0, 8).map((item) => {
                    const product = products.find(
                      (entry) => String(entry.id) === String(item.product_id)
                    );

                    return (
                      <tr
                        key={item.id ?? item.product_id}
                        className="transition hover:bg-slate-50"
                      >
                        <td className="px-6 py-4 font-semibold text-slate-800">
                          {product?.name ?? 'Product not found'}
                        </td>

                        <td className="px-6 py-4 text-slate-500">
                          #{item.product_id}
                        </td>

                        <td className="px-6 py-4">
                          <span className="inline-flex items-center gap-1.5 font-bold text-amber-700">
                            <AlertTriangle size={15} />
                            {Number(item.quantity) || 0} units
                          </span>
                        </td>

                        <td className="px-6 py-4 text-slate-500">
                          {formatDate(item.updated_at)}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            <div className="space-y-3 p-4 md:hidden">
              {lowStock.slice(0, 8).map((item) => {
                const product = products.find(
                  (entry) => String(entry.id) === String(item.product_id)
                );

                return (
                  <div
                    key={item.id ?? item.product_id}
                    className="rounded-xl border border-slate-200 p-4"
                  >
                    <div className="flex items-center justify-between gap-3">
                      <p className="font-semibold text-slate-800">
                        {product?.name ?? 'Product not found'}
                      </p>
                      <span className="rounded-full bg-amber-50 px-3 py-1 text-xs font-semibold text-amber-700">
                        {Number(item.quantity) || 0} units
                      </span>
                    </div>

                    <p className="mt-2 text-xs text-slate-500">
                      Product ID: #{item.product_id}
                    </p>

                    <p className="mt-2 text-xs text-slate-400">
                      Updated: {formatDate(item.updated_at)}
                    </p>
                  </div>
                );
              })}
            </div>
          </>
        )}
      </div>

      {/* Recent orders */}
      <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
        <SectionHeading
          title="Recent orders"
          description="Latest order records from the Order Service."
          link="/orders"
          linkText="View all orders"
        />

        {loading ? (
          <SkeletonRows />
        ) : orderServiceError ? (
          <div className="flex items-center gap-3 p-6 text-sm text-amber-700">
            <AlertTriangle size={18} />
            Orders could not be loaded. Check the Order Service response and authentication.
          </div>
        ) : recentOrders.length === 0 ? (
          <div className="p-10 text-center">
            <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-xl bg-slate-100 text-slate-500">
              <ShoppingCart size={23} />
            </div>

            <p className="mt-3 font-semibold text-slate-800">
              No orders yet
            </p>
            <p className="mt-1 text-sm text-slate-500">
              New orders will appear here.
            </p>
          </div>
        ) : (
          <>
            <div className="hidden overflow-x-auto md:block">
              <table className="w-full text-left text-sm">
                <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
                  <tr>
                    <th className="px-6 py-4 font-semibold">Order</th>
                    <th className="px-6 py-4 font-semibold">Status</th>
                    <th className="px-6 py-4 font-semibold">Order total</th>
                    <th className="px-6 py-4 font-semibold">Date</th>
                  </tr>
                </thead>

                <tbody className="divide-y divide-slate-100">
                  {recentOrders.map((order) => (
                    <tr
                      key={order.id ?? order.order_number}
                      className="transition hover:bg-slate-50"
                    >
                      <td className="px-6 py-4 font-semibold text-slate-800">
                        {order.order_number ?? `Order #${order.id}`}
                      </td>

                      <td className="px-6 py-4">
                        <StatusBadge status={order.status} />
                      </td>

                      <td className="px-6 py-4 font-semibold text-slate-800">
                        {formatCurrency(order.total_amount)}
                      </td>

                      <td className="px-6 py-4 text-slate-500">
                        {formatDate(order.created_at)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="space-y-3 p-4 md:hidden">
              {recentOrders.map((order) => (
                <div
                  key={order.id ?? order.order_number}
                  className="rounded-xl border border-slate-200 p-4"
                >
                  <div className="flex items-center justify-between gap-3">
                    <p className="font-semibold text-slate-800">
                      {order.order_number ?? `Order #${order.id}`}
                    </p>
                    <StatusBadge status={order.status} />
                  </div>

                  <div className="mt-3 flex items-center justify-between">
                    <span className="text-xs text-slate-500">Order total</span>
                    <span className="font-bold text-slate-900">
                      {formatCurrency(order.total_amount)}
                    </span>
                  </div>

                  <p className="mt-2 flex items-center gap-2 text-xs text-slate-400">
                    <Clock size={13} />
                    {formatDate(order.created_at)}
                  </p>
                </div>
              ))}
            </div>
          </>
        )}
      </div>


      {/* Coupon Management */}
      <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
        <div className="border-b border-slate-100 p-5 md:p-6">
          <h2 className="text-lg font-bold text-slate-900">
            Coupon Management
          </h2>
          <p className="mt-1 text-sm text-slate-500">
            Create discount coupons and manage promotional offers.
          </p>
        </div>

        <form onSubmit={createCoupon} className="space-y-5 p-5 md:p-6">
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <div>
              <label className="mb-1.5 block text-sm font-medium text-slate-700">
                Coupon Code
              </label>
              <input
                type="text"
                required
                minLength={3}
                maxLength={40}
                value={couponForm.code}
                onChange={(e) =>
                  setCouponForm({ ...couponForm, code: e.target.value.toUpperCase() })
                }
                placeholder="WELCOME10"
                className="w-full rounded-xl border border-slate-300 px-3 py-2.5 text-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
              />
            </div>

            <div>
              <label className="mb-1.5 block text-sm font-medium text-slate-700">
                Discount Type
              </label>
              <select
                value={couponForm.discount_type}
                onChange={(e) =>
                  setCouponForm({ ...couponForm, discount_type: e.target.value })
                }
                className="w-full rounded-xl border border-slate-300 px-3 py-2.5 text-sm outline-none focus:border-blue-500"
              >
                <option value="PERCENT">Percentage (%)</option>
                <option value="FIXED">Fixed Amount (₹)</option>
              </select>
            </div>

            <div>
              <label className="mb-1.5 block text-sm font-medium text-slate-700">
                Discount Value
              </label>
              <input
                type="number"
                required
                min="0.01"
                max={couponForm.discount_type === 'PERCENT' ? 100 : undefined}
                step="0.01"
                value={couponForm.discount_value}
                onChange={(e) =>
                  setCouponForm({ ...couponForm, discount_value: e.target.value })
                }
                placeholder="10"
                className="w-full rounded-xl border border-slate-300 px-3 py-2.5 text-sm outline-none focus:border-blue-500"
              />
            </div>

            <div>
              <label className="mb-1.5 block text-sm font-medium text-slate-700">
                Minimum Order Amount (₹)
              </label>
              <input
                type="number"
                min="0"
                step="0.01"
                value={couponForm.minimum_order_amount}
                onChange={(e) =>
                  setCouponForm({ ...couponForm, minimum_order_amount: e.target.value })
                }
                className="w-full rounded-xl border border-slate-300 px-3 py-2.5 text-sm outline-none focus:border-blue-500"
              />
            </div>

            <div>
              <label className="mb-1.5 block text-sm font-medium text-slate-700">
                Maximum Discount (₹)
              </label>
              <input
                type="number"
                min="0.01"
                step="0.01"
                value={couponForm.maximum_discount_amount}
                onChange={(e) =>
                  setCouponForm({ ...couponForm, maximum_discount_amount: e.target.value })
                }
                placeholder="Optional"
                className="w-full rounded-xl border border-slate-300 px-3 py-2.5 text-sm outline-none focus:border-blue-500"
              />
            </div>

            <div>
              <label className="mb-1.5 block text-sm font-medium text-slate-700">
                Usage Limit
              </label>
              <input
                type="number"
                min="1"
                step="1"
                value={couponForm.usage_limit}
                onChange={(e) =>
                  setCouponForm({ ...couponForm, usage_limit: e.target.value })
                }
                placeholder="Unlimited"
                className="w-full rounded-xl border border-slate-300 px-3 py-2.5 text-sm outline-none focus:border-blue-500"
              />
            </div>

            <div>
              <label className="mb-1.5 block text-sm font-medium text-slate-700">
                Start Date
              </label>
              <input
                type="datetime-local"
                value={couponForm.starts_at}
                onChange={(e) =>
                  setCouponForm({ ...couponForm, starts_at: e.target.value })
                }
                className="w-full rounded-xl border border-slate-300 px-3 py-2.5 text-sm outline-none focus:border-blue-500"
              />
            </div>

            <div>
              <label className="mb-1.5 block text-sm font-medium text-slate-700">
                Expiry Date
              </label>
              <input
                type="datetime-local"
                value={couponForm.expires_at}
                min={couponForm.starts_at || undefined}
                onChange={(e) =>
                  setCouponForm({ ...couponForm, expires_at: e.target.value })
                }
                className="w-full rounded-xl border border-slate-300 px-3 py-2.5 text-sm outline-none focus:border-blue-500"
              />
            </div>
          </div>

          {couponError && (
            <p className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">
              {couponError}
            </p>
          )}

          {couponMessage && (
            <p className="rounded-xl bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
              {couponMessage}
            </p>
          )}

          <button
            type="submit"
            disabled={couponSaving}
            className="rounded-xl bg-blue-600 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {couponSaving ? 'Creating Coupon...' : 'Create Coupon'}
          </button>
        </form>
      </div>


      {/* Existing Coupons */}
      <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 p-5">
          <div>
            <h3 className="text-lg font-bold text-slate-900">
              Existing Coupons
            </h3>
            <p className="mt-1 text-sm text-slate-500">
              Track coupon usage and manage active offers.
            </p>
          </div>

          <button
            type="button"
            onClick={async () => {
              setCouponLoading(true);
              setCouponError('');
              try {
                const response = await api.get('/coupons');
                setCoupons(Array.isArray(response.data) ? response.data : []);
              } catch (error) {
                setCouponError(
                  error.response?.data?.detail || 'Unable to refresh coupons.'
                );
              } finally {
                setCouponLoading(false);
              }
            }}
            disabled={couponLoading}
            className="inline-flex items-center gap-2 rounded-xl border border-slate-200 px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-50 disabled:opacity-60"
          >
            <RefreshCw size={15} className={couponLoading ? 'animate-spin' : ''} />
            Refresh
          </button>
        </div>

        {couponLoading ? (
          <SkeletonRows />
        ) : coupons.length === 0 ? (
          <div className="p-10 text-center">
            <p className="font-semibold text-slate-700">No coupons found</p>
            <p className="mt-1 text-sm text-slate-500">
              Create your first coupon using the form above.
            </p>
          </div>
        ) : (
          <>
            <div className="hidden overflow-x-auto md:block">
              <table className="w-full text-left text-sm">
                <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
                  <tr>
                    <th className="px-5 py-4">Coupon</th>
                    <th className="px-5 py-4">Discount</th>
                    <th className="px-5 py-4">Usage</th>
                    <th className="px-5 py-4">Expiry</th>
                    <th className="px-5 py-4">Status</th>
                    <th className="px-5 py-4">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {coupons.map((coupon) => (
                    <tr key={coupon.id} className="hover:bg-slate-50/70">
                      <td className="px-5 py-4">
                        <p className="font-bold text-slate-900">{coupon.code}</p>
                        <p className="mt-1 text-xs text-slate-400">
                          Minimum: {formatCurrency(coupon.minimum_order_amount)}
                        </p>
                      </td>

                      <td className="px-5 py-4 font-semibold text-slate-800">
                        {coupon.discount_type === 'PERCENT'
                          ? `${coupon.discount_value}%`
                          : formatCurrency(coupon.discount_value)}
                        {coupon.maximum_discount_amount != null && (
                          <p className="mt-1 text-xs font-normal text-slate-400">
                            Max: {formatCurrency(coupon.maximum_discount_amount)}
                          </p>
                        )}
                      </td>

                      <td className="px-5 py-4">
                        <p className="font-semibold text-slate-800">
                          {coupon.usage_count} / {coupon.usage_limit ?? '∞'}
                        </p>
                        {coupon.usage_limit != null && (
                          <div className="mt-2 h-1.5 w-24 overflow-hidden rounded-full bg-slate-100">
                            <div
                              className="h-full rounded-full bg-blue-500"
                              style={{
                                width: `${Math.min(
                                  100,
                                  (coupon.usage_count / coupon.usage_limit) * 100
                                )}%`,
                              }}
                            />
                          </div>
                        )}
                      </td>

                      <td className="px-5 py-4 text-slate-500">
                        {coupon.expires_at ? formatDate(coupon.expires_at) : 'No expiry'}
                      </td>

                      <td className="px-5 py-4">
                        <StatusBadge
                          status={coupon.is_active ? 'Active' : 'Inactive'}
                        />
                      </td>

                      <td className="px-5 py-4">
                        <button
                          type="button"
                          onClick={() => toggleCouponStatus(coupon)}
                          className={`rounded-lg px-3 py-2 text-xs font-semibold transition ${
                            coupon.is_active
                              ? 'bg-red-50 text-red-600 hover:bg-red-100'
                              : 'bg-emerald-50 text-emerald-700 hover:bg-emerald-100'
                          }`}
                        >
                          {coupon.is_active ? 'Deactivate' : 'Activate'}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="space-y-3 p-4 md:hidden">
              {coupons.map((coupon) => (
                <div
                  key={coupon.id}
                  className="rounded-xl border border-slate-200 p-4"
                >
                  <div className="flex items-center justify-between gap-3">
                    <p className="font-bold text-slate-900">{coupon.code}</p>
                    <StatusBadge
                      status={coupon.is_active ? 'Active' : 'Inactive'}
                    />
                  </div>

                  <div className="mt-3 grid grid-cols-2 gap-3 text-sm">
                    <div>
                      <p className="text-xs text-slate-400">Discount</p>
                      <p className="font-semibold text-slate-800">
                        {coupon.discount_type === 'PERCENT'
                          ? `${coupon.discount_value}%`
                          : formatCurrency(coupon.discount_value)}
                      </p>
                    </div>
                    <div>
                      <p className="text-xs text-slate-400">Usage</p>
                      <p className="font-semibold text-slate-800">
                        {coupon.usage_count} / {coupon.usage_limit ?? '∞'}
                      </p>
                    </div>
                    <div>
                      <p className="text-xs text-slate-400">Minimum order</p>
                      <p className="font-semibold text-slate-800">
                        {formatCurrency(coupon.minimum_order_amount)}
                      </p>
                    </div>
                    <div>
                      <p className="text-xs text-slate-400">Expiry</p>
                      <p className="font-semibold text-slate-800">
                        {coupon.expires_at ? formatDate(coupon.expires_at) : 'No expiry'}
                      </p>
                    </div>
                  </div>

                  <button
                    type="button"
                    onClick={() => toggleCouponStatus(coupon)}
                    className={`mt-4 w-full rounded-lg px-3 py-2.5 text-sm font-semibold ${
                      coupon.is_active
                        ? 'bg-red-50 text-red-600'
                        : 'bg-emerald-50 text-emerald-700'
                    }`}
                  >
                    {coupon.is_active ? 'Deactivate Coupon' : 'Activate Coupon'}
                  </button>
                </div>
              ))}
            </div>
          </>
        )}
      </div>


      {/* Quick links */}
      <div>
        <div className="mb-4">
          <h2 className="text-lg font-bold text-slate-900">
            Quick navigation
          </h2>
          <p className="mt-1 text-sm text-slate-500">
            Jump directly to the management sections.
          </p>
        </div>

        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          {[
            {
              title: 'Manage Products',
              description: 'Add, edit, and deactivate products.',
              icon: Package,
              link: '/products',
              color: 'blue',
            },
            {
              title: 'Manage Inventory',
              description: 'Monitor available stock quantities.',
              icon: Boxes,
              link: '/inventory',
              color: 'green',
            },
            {
              title: 'Manage Orders',
              description: 'Review customer orders and status.',
              icon: ShoppingCart,
              link: '/orders',
              color: 'violet',
            },
            {
              title: 'Customers',
              description: 'View registered customer accounts.',
              icon: UsersIcon,
              link: '/customers',
              color: 'amber',
            },
          ].map((item) => {
            const Icon = item.icon;

            return (
              <Link
                key={item.title}
                to={item.link}
                className="group flex items-center gap-4 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm transition hover:-translate-y-1 hover:border-blue-200 hover:shadow-md"
              >
                <div className={`rounded-xl p-3 ${
                  item.color === 'blue'
                    ? 'bg-blue-50 text-blue-600'
                    : item.color === 'green'
                    ? 'bg-emerald-50 text-emerald-600'
                    : item.color === 'violet'
                    ? 'bg-violet-50 text-violet-600'
                    : 'bg-amber-50 text-amber-600'
                }`}>
                  <Icon size={21} />
                </div>

                <div className="min-w-0 flex-1">
                  <p className="font-semibold text-slate-800">
                    {item.title}
                  </p>
                  <p className="mt-1 text-xs text-slate-500">
                    {item.description}
                  </p>
                </div>

                <ArrowRight
                  size={17}
                  className="shrink-0 text-slate-300 transition group-hover:translate-x-1 group-hover:text-blue-600"
                />
              </Link>
            );
          })}
        </div>
      </div>
    </section>
  );
}

function UsersIcon(props) {
  return <PackageCheck {...props} />;
}

export default App;
