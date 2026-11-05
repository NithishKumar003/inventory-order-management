
import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  RefreshCw,
  Package,
  CheckCircle2,
  Clock3,
  Truck,
  MapPin,
  Receipt,
  ShoppingBag,
  CalendarDays,
  CreditCard,
  AlertCircle,
  RotateCcw,
  X,
  ShieldCheck,
  XCircle,
} from 'lucide-react';

import api from '../services/api';

const formatCurrency = (value) =>
  `₹${Number(value ?? 0).toFixed(2)}`;

const formatDate = (value) => {
  if (!value) return 'Not available';

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) return value;

  return date.toLocaleString('en-IN', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
};

const steps = [
  {
    label: 'Order Placed',
    description: 'Your order has been received.',
    icon: ShoppingBag,
  },
  {
    label: 'Confirmed',
    description: 'Your order has been confirmed.',
    icon: CheckCircle2,
  },
  {
    label: 'Processing',
    description: 'Your items are being prepared.',
    icon: Package,
  },
  {
    label: 'Shipped',
    description: 'Your order is on its way.',
    icon: Truck,
  },
  {
    label: 'Delivered',
    description: 'Your order has been delivered.',
    icon: CheckCircle2,
  },
];

const statusOrder = [
  'pending',
  'confirmed',
  'processing',
  'shipped',
  'delivered',
];

function OrderTimeline({ status }) {
  const normalizedStatus = String(status || '').toLowerCase();
  const currentIndex = statusOrder.indexOf(normalizedStatus);

  if (
    normalizedStatus === 'cancelled' ||
    normalizedStatus === 'returned'
  ) {
    return (
      <div className="mt-5 flex items-start gap-3 rounded-xl bg-red-50 p-4">
        <AlertCircle className="mt-0.5 text-red-600" size={22} />
        <div>
          <p className="font-semibold capitalize text-red-700">
            Order {normalizedStatus}
          </p>
          <p className="mt-1 text-sm text-red-600">
            This order is currently marked as {normalizedStatus}.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="mt-6">
      <div className="space-y-5">
        {steps.map((step, index) => {
          const Icon = step.icon;
          const completed = currentIndex >= index;
          const active = currentIndex === index;

          return (
            <div key={step.label} className="flex gap-4">
              <div className="flex flex-col items-center">
                <div
                  className={`flex h-10 w-10 items-center justify-center rounded-full ${
                    completed
                      ? 'bg-blue-600 text-white'
                      : 'bg-slate-100 text-slate-400'
                  } ${active ? 'ring-4 ring-blue-100' : ''}`}
                >
                  <Icon size={19} />
                </div>

                {index !== steps.length - 1 && (
                  <div
                    className={`mt-1 h-8 w-0.5 ${
                      currentIndex > index
                        ? 'bg-blue-600'
                        : 'bg-slate-200'
                    }`}
                  />
                )}
              </div>

              <div className="pt-1">
                <p
                  className={`font-semibold ${
                    completed ? 'text-slate-900' : 'text-slate-400'
                  }`}
                >
                  {step.label}
                </p>
                <p className="mt-1 text-sm text-slate-500">
                  {step.description}
                </p>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function LoadingSkeleton() {
  return (
    <div className="animate-pulse space-y-6">
      <div className="h-5 w-36 rounded bg-slate-200" />
      <div className="h-24 rounded-2xl bg-slate-200" />
      <div className="h-72 rounded-2xl bg-slate-200" />
      <div className="h-48 rounded-2xl bg-slate-200" />
    </div>
  );
}

function PaymentStatus({ status }) {
  const normalizedStatus = String(status || '').toUpperCase();

  if (normalizedStatus === 'SUCCESS') {
    return (
      <div className="flex items-center gap-2 rounded-xl border border-emerald-200 bg-emerald-50 p-4">
        <CheckCircle2 size={25} className="shrink-0 text-emerald-600" />
        <div>
          <p className="font-bold text-emerald-800">
            Payment Successful
          </p>
          <p className="mt-1 text-xs text-emerald-700">
            Your payment has been received successfully.
          </p>
        </div>
      </div>
    );
  }

  if (normalizedStatus === 'PENDING') {
    return (
      <div className="flex items-center gap-2 rounded-xl border border-amber-200 bg-amber-50 p-4">
        <Clock3 size={25} className="shrink-0 text-amber-600" />
        <div>
          <p className="font-bold text-amber-800">
            Payment Pending
          </p>
          <p className="mt-1 text-xs text-amber-700">
            Your payment is awaiting confirmation.
          </p>
        </div>
      </div>
    );
  }

  if (normalizedStatus === 'FAILED') {
    return (
      <div className="flex items-center gap-2 rounded-xl border border-red-200 bg-red-50 p-4">
        <XCircle size={25} className="shrink-0 text-red-600" />
        <div>
          <p className="font-bold text-red-800">
            Payment Failed
          </p>
          <p className="mt-1 text-xs text-red-700">
            Your payment could not be completed.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex items-center gap-2 rounded-xl border border-slate-200 bg-slate-50 p-4">
      <AlertCircle size={23} className="shrink-0 text-slate-500" />
      <div>
        <p className="font-bold text-slate-700">
          {normalizedStatus || 'Payment Status Unavailable'}
        </p>
        <p className="mt-1 text-xs text-slate-500">
          Please refresh to check the latest payment information.
        </p>
      </div>
    </div>
  );
}

export default function OrderDetails() {
  const { orderId } = useParams();
  const navigate = useNavigate();

  const [order, setOrder] = useState(null);
  const [payment, setPayment] = useState(null);
  const [paymentNotFound, setPaymentNotFound] = useState(false);
  const [paymentError, setPaymentError] = useState('');
  const [paymentLoading, setPaymentLoading] = useState(true);

  const [returns, setReturns] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const [selectedItem, setSelectedItem] = useState(null);
  const [returnQuantity, setReturnQuantity] = useState(1);
  const [returnReason, setReturnReason] = useState('');
  const [submittingReturn, setSubmittingReturn] = useState(false);
  const [returnMessage, setReturnMessage] = useState('');
  const [returnError, setReturnError] = useState('');

  
  async function loadOrder() {
    setLoading(true);
    setError('');

    try {
      const orderResponse = await api.get(`/orders/${orderId}`);
      setOrder(orderResponse.data);

      // Load payment information independently.
      setPaymentLoading(true);
      setPayment(null);
      setPaymentNotFound(false);
      setPaymentError('');

      try {
        const paymentResponse = await api.get(
          `/payments/order/${orderId}`
        );

        setPayment(paymentResponse.data);

        if (paymentResponse.data === null) {
          setPaymentNotFound(true);
        }
      } catch (paymentErr) {
        if (paymentErr.response?.status === 404) {
          setPaymentNotFound(true);
        } else {
          console.error('Payment information error:', paymentErr);

          setPaymentError(
            paymentErr.response?.data?.detail ||
              'Unable to load payment information.'
          );
        }
      } finally {
        setPaymentLoading(false);
      }

      // Load return history separately.
      try {
        const returnsResponse = await api.get('/returns/me');

        setReturns(
          Array.isArray(returnsResponse.data)
            ? returnsResponse.data
            : []
        );
      } catch (returnErr) {
        console.error('Return history error:', returnErr);
        setReturns([]);
      }
    } catch (err) {
      console.error('Order details error:', err);

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

  function getRemainingReturnQuantity(item) {
    const alreadyRequested = returns
      .filter(
        (returnRequest) =>
          Number(returnRequest.order_id) === Number(order.id) &&
          Number(returnRequest.order_item_id) === Number(item.id) &&
          ['PENDING', 'APPROVED', 'COMPLETED'].includes(
            String(returnRequest.status).toUpperCase()
          )
      )
      .reduce(
        (total, returnRequest) =>
          total + Number(returnRequest.quantity || 0),
        0
      );

    const available =
      Number(item.quantity || 0) -
      Number(item.cancelled_quantity || 0);

    return Math.max(0, available - alreadyRequested);
  }

  function openReturnModal(item) {
    setSelectedItem(item);
    setReturnQuantity(1);
    setReturnReason('');
    setReturnMessage('');
    setReturnError('');
  }

  function closeReturnModal() {
    if (submittingReturn) return;

    setSelectedItem(null);
    setReturnReason('');
    setReturnError('');
  }

  async function submitReturnRequest(event) {
    event.preventDefault();

    if (!selectedItem) return;

    const reason = returnReason.trim();

    if (reason.length < 5) {
      setReturnError('Please enter at least 5 characters.');
      return;
    }

    if (reason.length > 500) {
      setReturnError('Reason cannot exceed 500 characters.');
      return;
    }

    const remaining = getRemainingReturnQuantity(selectedItem);

    if (
      returnQuantity < 1 ||
      returnQuantity > remaining
    ) {
      setReturnError('Please select a valid return quantity.');
      return;
    }

    setSubmittingReturn(true);
    setReturnError('');

    try {
      await api.post('/returns', {
        order_id: Number(order.id),
        order_item_id: Number(selectedItem.id),
        quantity: Number(returnQuantity),
        reason,
        idempotency_key: crypto.randomUUID(),
      });

      setReturnMessage(
        'Your return request has been submitted successfully.'
      );

      setSelectedItem(null);
      setReturnReason('');

      await loadOrder();
    } catch (err) {
      console.error('Return request error:', err);

      setReturnError(
        err.response?.data?.detail ||
        'Unable to submit your return request. Please try again.'
      );
    } finally {
      setSubmittingReturn(false);
    }
  }

  if (loading && !order) {
    return (
      <section className="page-enter mx-auto max-w-6xl space-y-6 p-5 md:p-8">
        <LoadingSkeleton />
      </section>
    );
  }

  if (error || !order) {
    return (
      <section className="page-enter mx-auto max-w-3xl p-6">
        <div className="rounded-2xl border border-red-100 bg-white p-8 text-center shadow-sm">
          <AlertCircle className="mx-auto text-red-500" size={38} />

          <h2 className="mt-4 text-xl font-bold text-slate-900">
            Unable to load order
          </h2>

          <p role="alert" className="mt-2 text-sm text-red-600">
            {error || 'Order not found.'}
          </p>

          <div className="mt-6 flex flex-wrap justify-center gap-3">
            <button
              onClick={loadOrder}
              className="flex items-center gap-2 rounded-xl bg-blue-600 px-5 py-3 font-semibold text-white hover:bg-blue-700"
            >
              <RefreshCw size={17} />
              Try Again
            </button>

            <button
              onClick={() => navigate('/orders')}
              className="rounded-xl border border-slate-200 px-5 py-3 font-semibold text-slate-700 hover:bg-slate-50"
            >
              Back to My Orders
            </button>
          </div>
        </div>
      </section>
    );
  }

  const items = Array.isArray(order.items) ? order.items : [];

  const orderDelivered =
    String(order.status || '').toLowerCase() === 'delivered';

  return (
    <section className="page-enter mx-auto max-w-6xl space-y-6 p-5 md:p-8">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <button
          onClick={() => navigate('/orders')}
          className="flex items-center gap-2 text-sm font-semibold text-slate-600 hover:text-blue-600"
        >
          <ArrowLeft size={18} />
          Back to My Orders
        </button>

        <button
          onClick={loadOrder}
          disabled={loading}
          className="flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-semibold text-slate-600 shadow-sm hover:bg-slate-50 disabled:opacity-50"
        >
          <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
          Refresh
        </button>
      </div>

      {returnMessage && (
        <div
          role="status"
          className="rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm font-medium text-emerald-700"
        >
          {returnMessage}
        </div>
      )}

      {/* Order heading */}
      <div className="rounded-2xl bg-gradient-to-r from-blue-700 to-indigo-700 p-6 text-white shadow-lg md:p-8">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <p className="text-sm font-medium text-blue-100">
              Order Details
            </p>

            <h1 className="mt-2 text-2xl font-bold md:text-3xl">
              {order.order_number || `Order #${order.id}`}
            </h1>

            <p className="mt-2 flex items-center gap-2 text-sm text-blue-100">
              <CalendarDays size={16} />
              {formatDate(order.created_at)}
            </p>
          </div>

          <div className="rounded-xl border border-white/20 bg-white/10 px-5 py-3 backdrop-blur">
            <p className="text-xs text-blue-100">Order Total</p>
            <p className="mt-1 text-2xl font-bold">
              {formatCurrency(order.total_amount)}
            </p>
          </div>
        </div>
      </div>

      {/* Main layout */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="space-y-6 lg:col-span-2">
          {/* Order tracking */}
          <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <div className="flex items-center gap-3">
              <div className="rounded-xl bg-blue-50 p-3 text-blue-600">
                <Truck size={23} />
              </div>

              <div>
                <h2 className="text-lg font-bold text-slate-900">
                  Order Tracking
                </h2>

                <p className="text-sm text-slate-500">
                  Current status: {order.status || 'Unknown'}
                </p>
              </div>
            </div>

            <OrderTimeline status={order.status} />
          </div>

          {/* Products */}
          <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <div className="flex items-center justify-between gap-3">
              <h2 className="text-lg font-bold text-slate-900">
                Ordered Products
              </h2>

              <span className="rounded-full bg-blue-50 px-3 py-1 text-xs font-semibold text-blue-700">
                {items.length} {items.length === 1 ? 'Item' : 'Items'}
              </span>
            </div>

            <div className="mt-5 divide-y divide-slate-100">
              {items.length > 0 ? (
                items.map((item) => {
                  const remainingQuantity =
                    getRemainingReturnQuantity(item);

                  return (
                    <div
                      key={item.id}
                      className="py-5 first:pt-0 last:pb-0"
                    >
                      <div className="flex flex-wrap items-center justify-between gap-4">
                        <div className="flex min-w-0 items-center gap-4">
                          <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-xl bg-slate-100 text-slate-500">
                            <Package size={25} />
                          </div>

                          <div className="min-w-0">
                            <p className="break-words font-semibold text-slate-800">
                              {item.product_name ||
                                `Product #${item.product_id}`}
                            </p>

                            <p className="mt-1 text-sm text-slate-500">
                              Quantity: {item.quantity}
                            </p>

                            <p className="mt-1 text-sm text-slate-500">
                              Item status: {item.status || 'Not available'}
                            </p>

                            {Number(item.cancelled_quantity) > 0 && (
                              <p className="mt-1 text-sm text-red-600">
                                Cancelled quantity: {item.cancelled_quantity}
                              </p>
                            )}
                          </div>
                        </div>

                        <p className="font-bold text-slate-900">
                          {formatCurrency(item.line_subtotal)}
                        </p>
                      </div>

                      {/* Return button */}
                      {orderDelivered && remainingQuantity > 0 && (
                        <div className="mt-4 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-emerald-100 bg-emerald-50 p-4">
                          <div>
                            <p className="text-sm font-semibold text-emerald-800">
                              Eligible for return
                            </p>

                            <p className="mt-1 text-xs text-emerald-700">
                              {remainingQuantity} unit(s) available for return.
                            </p>
                          </div>

                          <button
                            onClick={() => openReturnModal(item)}
                            className="flex items-center gap-2 rounded-xl bg-emerald-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-emerald-700"
                          >
                            <RotateCcw size={16} />
                            Request Return
                          </button>
                        </div>
                      )}

                      {/* Existing return requests */}
                      {returns
                        .filter(
                          (returnRequest) =>
                            Number(returnRequest.order_item_id) ===
                              Number(item.id) &&
                            Number(returnRequest.order_id) ===
                              Number(order.id)
                        )
                        .map((returnRequest) => (
                          <div
                            key={returnRequest.id}
                            className="mt-3 rounded-xl border border-slate-200 bg-slate-50 p-4"
                          >
                            <div className="flex flex-wrap items-center justify-between gap-2">
                              <p className="text-sm font-semibold text-slate-800">
                                Return #{returnRequest.id}
                              </p>

                              <span className="rounded-full bg-amber-100 px-3 py-1 text-xs font-bold text-amber-800">
                                {returnRequest.status}
                              </span>
                            </div>

                            <p className="mt-2 text-sm text-slate-600">
                              Quantity: {returnRequest.quantity}
                            </p>

                            <p className="mt-1 text-sm text-slate-600">
                              Reason: {returnRequest.reason}
                            </p>

                            <p className="mt-1 text-sm text-slate-600">
                              Refund amount: {formatCurrency(returnRequest.refund_amount)}
                            </p>

                            <p className="mt-1 text-sm text-slate-600">
                              Refund status: {returnRequest.refund_status}
                            </p>
                          </div>
                        ))}
                    </div>
                  );
                })
              ) : (
                <p className="py-6 text-center text-sm text-slate-500">
                  No product items found for this order.
                </p>
              )}
            </div>
          </div>

          {/* Shipping address */}
          <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <div className="flex items-center gap-3">
              <div className="rounded-xl bg-emerald-50 p-3 text-emerald-600">
                <MapPin size={22} />
              </div>

              <div>
                <h2 className="font-bold text-slate-900">
                  Shipping Address
                </h2>

                <p className="text-sm text-slate-500">
                  Delivery destination
                </p>
              </div>
            </div>

            <p className="mt-4 whitespace-pre-wrap rounded-xl bg-slate-50 p-4 text-sm leading-6 text-slate-700">
              {order.shipping_address || 'No shipping address available.'}
            </p>
          </div>
        </div>

        {/* Summary sidebar */}
        <aside className="space-y-6">
          {/* Order summary */}
          <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <div className="flex items-center gap-3">
              <div className="rounded-xl bg-violet-50 p-3 text-violet-600">
                <Receipt size={22} />
              </div>

              <h2 className="text-lg font-bold text-slate-900">
                Order Summary
              </h2>
            </div>

            <div className="mt-6 space-y-4 text-sm">
              <div className="flex justify-between gap-3">
                <span className="text-slate-500">Subtotal</span>
                <span className="font-medium text-slate-800">
                  {formatCurrency(order.subtotal)}
                </span>
              </div>

              <div className="flex justify-between gap-3">
                <span className="text-slate-500">Tax</span>
                <span className="font-medium text-slate-800">
                  {formatCurrency(order.tax_amount)}
                </span>
              </div>

              <div className="flex justify-between gap-3">
                <span className="text-slate-500">Discount</span>
                <span className="font-medium text-emerald-600">
                  - {formatCurrency(order.discount_amount)}
                </span>
              </div>

              <div className="flex justify-between gap-3">
                <span className="text-slate-500">Shipping</span>
                <span className="font-medium text-slate-800">
                  {formatCurrency(order.shipping_amount)}
                </span>
              </div>

              <div className="border-t border-dashed border-slate-200 pt-4">
                <div className="flex justify-between gap-3 text-base font-bold">
                  <span className="text-slate-900">Total Amount</span>
                  <span className="text-blue-700">
                    {formatCurrency(order.total_amount)}
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Payment information */}
          <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <div className="flex items-center gap-3">
              <div className="rounded-xl bg-amber-50 p-3 text-amber-600">
                <CreditCard size={22} />
              </div>

              <h2 className="font-bold text-slate-900">
                Payment Information
              </h2>
            </div>

            <div className="mt-5">
              {paymentLoading ? (
                <div className="animate-pulse space-y-3">
                  <div className="h-12 rounded-xl bg-slate-100" />
                  <div className="h-4 w-2/3 rounded bg-slate-100" />
                </div>
              ) : payment ? (
                <div className="space-y-4">
                  <PaymentStatus status={payment.status} />

                  <div className="space-y-3 text-sm">
                    <div className="flex justify-between gap-3">
                      <span className="text-slate-500">Payment method</span>
                      <span className="font-medium text-slate-800">
                        {order.payment_method || 'Stripe Checkout'}
                      </span>
                    </div>

                    <div className="flex justify-between gap-3">
                      <span className="text-slate-500">Payment amount</span>
                      <span className="font-semibold text-slate-900">
                        {formatCurrency(payment.amount)}
                      </span>
                    </div>

                    <div className="flex justify-between gap-3">
                      <span className="text-slate-500">Payment ID</span>
                      <span className="font-medium text-slate-800">
                        #{payment.payment_id}
                      </span>
                    </div>

                    {payment.transaction_reference && (
                      <div className="border-t border-slate-100 pt-3">
                        <p className="text-slate-500">
                          Transaction reference
                        </p>
                        <p className="mt-1 break-all text-xs font-medium text-slate-700">
                          {payment.transaction_reference}
                        </p>
                      </div>
                    )}

                    <div className="flex justify-between gap-3 border-t border-slate-100 pt-3">
                      <span className="text-slate-500">Payment date</span>
                      <span className="text-right font-medium text-slate-800">
                        {formatDate(payment.created_at)}
                      </span>
                    </div>
                  </div>

                  {String(payment.status).toUpperCase() === 'SUCCESS' && (
                    <div className="flex items-center gap-2 border-t border-emerald-100 pt-3 text-xs font-medium text-emerald-700">
                      <ShieldCheck size={17} />
                      Secure payment confirmation recorded.
                    </div>
                  )}

                  {payment.failure_reason && (
                    <div className="rounded-xl bg-red-50 p-3 text-sm text-red-700">
                      {payment.failure_reason}
                    </div>
                  )}
                </div>
              ) : paymentNotFound ? (
                <div className="rounded-xl border border-amber-200 bg-amber-50 p-4">
                  <div className="flex items-center gap-2 text-amber-800">
                    <AlertCircle size={20} />
                    <p className="font-semibold">
                      No payment record found
                    </p>
                  </div>

                  <p className="mt-2 text-xs leading-5 text-amber-700">
                    No payment record is currently available for this order.
                    Refresh the page to check again.
                  </p>
                </div>
              ) : (
                <div className="rounded-xl border border-red-200 bg-red-50 p-4">
                  <p className="font-semibold text-red-800">
                    Unable to load payment
                  </p>
                  <p className="mt-2 text-xs leading-5 text-red-700">
                    {paymentError || 'Please refresh to try again.'}
                  </p>
                </div>
              )}
            </div>
          </div>

          {/* Help */}
          <div className="rounded-2xl bg-blue-50 p-5">
            <div className="flex items-center gap-2 text-blue-800">
              <Clock3 size={19} />
              <p className="font-semibold">Need help?</p>
            </div>

            <p className="mt-2 text-sm leading-6 text-blue-700">
              Keep your order number handy when contacting customer support.
            </p>
          </div>
        </aside>
      </div>

      {/* Return request modal */}
      {selectedItem && (
        <div className="fixed inset-0 z-50 flex items-center justify-center overflow-y-auto bg-slate-950/60 p-4">
          <div className="my-auto w-full max-w-lg rounded-2xl bg-white p-6 shadow-2xl">
            <div className="flex items-center justify-between gap-4">
              <div>
                <h2 className="text-xl font-bold text-slate-900">
                  Request a Return
                </h2>

                <p className="mt-1 text-sm text-slate-500">
                  {selectedItem.product_name}
                </p>
              </div>

              <button
                onClick={closeReturnModal}
                disabled={submittingReturn}
                className="rounded-lg p-2 text-slate-500 hover:bg-slate-100"
              >
                <X size={21} />
              </button>
            </div>

            <form
              onSubmit={submitReturnRequest}
              className="mt-6 space-y-5"
            >
              <div>
                <label className="mb-2 block text-sm font-semibold text-slate-700">
                  Return Quantity
                </label>

                <select
                  value={returnQuantity}
                  onChange={(event) =>
                    setReturnQuantity(Number(event.target.value))
                  }
                  className="w-full rounded-xl border border-slate-300 px-4 py-3 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
                >
                  {Array.from(
                    {
                      length: getRemainingReturnQuantity(selectedItem),
                    },
                    (_, index) => index + 1
                  ).map((quantity) => (
                    <option key={quantity} value={quantity}>
                      {quantity}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="mb-2 block text-sm font-semibold text-slate-700">
                  Reason for Return
                </label>

                <textarea
                  value={returnReason}
                  onChange={(event) =>
                    setReturnReason(event.target.value)
                  }
                  rows={4}
                  maxLength={500}
                  placeholder="Please explain why you want to return this product..."
                  className="w-full resize-none rounded-xl border border-slate-300 px-4 py-3 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
                />

                <p className="mt-1 text-right text-xs text-slate-400">
                  {returnReason.length}/500 characters
                </p>
              </div>

              {returnError && (
                <div
                  role="alert"
                  className="rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700"
                >
                  {returnError}
                </div>
              )}

              <div className="flex flex-wrap justify-end gap-3">
                <button
                  type="button"
                  onClick={closeReturnModal}
                  disabled={submittingReturn}
                  className="rounded-xl border border-slate-200 px-5 py-3 text-sm font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-50"
                >
                  Cancel
                </button>

                <button
                  type="submit"
                  disabled={submittingReturn}
                  className="flex items-center gap-2 rounded-xl bg-emerald-600 px-5 py-3 text-sm font-semibold text-white hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  <RotateCcw size={16} />
                  {submittingReturn ? 'Submitting...' : 'Submit Return'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </section>
  );
}
