
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Minus,
  Plus,
  Trash2,
  ShoppingBag,
  Package,
  ArrowRight,
  MapPin,
  ShieldCheck,
  CheckCircle2,
  AlertCircle,
  RefreshCw,
  ShoppingCart,
  X,
  CreditCard,
} from 'lucide-react';
import api from '../services/api';

function CartSkeleton() {
  return (
    <div className="grid gap-6 lg:grid-cols-3">
      <div className="space-y-4 lg:col-span-2">
        {[1, 2, 3].map((item) => (
          <div
            key={item}
            className="flex animate-pulse gap-4 rounded-2xl border border-slate-200 bg-white p-5"
          >
            <div className="h-24 w-24 shrink-0 rounded-xl bg-slate-200" />
            <div className="flex-1 space-y-3">
              <div className="h-5 w-2/3 rounded bg-slate-200" />
              <div className="h-4 w-1/3 rounded bg-slate-200" />
              <div className="h-8 w-28 rounded bg-slate-200" />
            </div>
          </div>
        ))}
      </div>
      <div className="h-80 animate-pulse rounded-2xl bg-slate-200" />
    </div>
  );
}

function formatPrice(value) {
  return `₹${Number(value || 0).toLocaleString('en-IN', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

export default function Cart() {
  const navigate = useNavigate();

  const [cart, setCart] = useState({
    items: [],
    item_count: 0,
    total_amount: 0,
  });

  const [shippingAddress, setShippingAddress] = useState('');
  const [couponCode, setCouponCode] = useState('');
  const [validated, setValidated] = useState(false);
  const [appliedCoupon, setAppliedCoupon] = useState(null);
  const [couponLoading, setCouponLoading] = useState(false);
  const [checkoutLoading, setCheckoutLoading] = useState(false);
  const [paymentReview, setPaymentReview] = useState(null);
  const [paymentRedirectLoading, setPaymentRedirectLoading] = useState(false);
  const [validationLoading, setValidationLoading] = useState(false);
  const [itemLoading, setItemLoading] = useState([]);
  const [clearLoading, setClearLoading] = useState(false);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');

  async function fetchCart(showLoader = true) {
    try {
      if (showLoader) setLoading(true);
      setError('');

      const response = await api.get('/cart');

      setCart({
        items: Array.isArray(response.data.items)
          ? response.data.items
          : [],
        item_count: response.data.item_count || 0,
        total_amount: response.data.total_amount || 0,
      });
    } catch (err) {
      setError(
        err.response?.data?.detail || 'Unable to load your cart.'
      );
    } finally {
      if (showLoader) setLoading(false);
    }
  }

  useEffect(() => {
    fetchCart();
  }, []);

  async function updateQuantity(productId, quantity) {
    if (quantity < 1 || checkoutLoading) return;
    if (itemLoading.includes(productId)) return;

    try {
      setItemLoading((previous) => [...previous, productId]);
      setError('');
      setMessage('');

      await api.put(`/cart/items/${productId}`, { quantity });

      setValidated(false);
      setMessage('Cart updated successfully.');
      await fetchCart(false);
    } catch (err) {
      setError(
        err.response?.data?.detail || 'Unable to update quantity.'
      );
    } finally {
      setItemLoading((previous) =>
        previous.filter((id) => id !== productId)
      );
    }
  }

  async function removeItem(productId) {
    if (checkoutLoading || itemLoading.includes(productId)) return;

    try {
      setItemLoading((previous) => [...previous, productId]);
      setError('');
      setMessage('');

      await api.delete(`/cart/items/${productId}`);

      setValidated(false);
      setMessage('Product removed from cart.');
      await fetchCart(false);
    } catch (err) {
      setError(
        err.response?.data?.detail || 'Unable to remove product.'
      );
    } finally {
      setItemLoading((previous) =>
        previous.filter((id) => id !== productId)
      );
    }
  }

  async function clearCart() {
    if (checkoutLoading || clearLoading) return;

    const confirmed = window.confirm(
      'Are you sure you want to remove all products from your cart?'
    );

    if (!confirmed) return;

    try {
      setClearLoading(true);
      setError('');
      setMessage('');

      await api.delete('/cart');

      setValidated(false);
      setMessage('Cart cleared successfully.');
      await fetchCart(false);
    } catch (err) {
      setError(
        err.response?.data?.detail || 'Unable to clear cart.'
      );
    } finally {
      setClearLoading(false);
    }
  }

  async function applyCoupon() {
    if (couponLoading || checkoutLoading) return;

    const code = couponCode.trim().toUpperCase();

    if (!code) {
      setError('Please enter a coupon code.');
      return;
    }

    if (!cart.items.length) {
      setError('Your cart is empty.');
      return;
    }

    setCouponLoading(true);
    setError('');
    setMessage('');

    try {
      const response = await api.post('/coupons/validate', {
        code,
        subtotal: Number(cart.total_amount),
      });

      setAppliedCoupon(response.data);
      setCouponCode(response.data.code);
      setValidated(false);
      setMessage('Coupon applied successfully!');
    } catch (error) {
      setAppliedCoupon(null);
      setError(
        error.response?.data?.detail || 'Unable to apply coupon.'
      );
    } finally {
      setCouponLoading(false);
    }
  }

  function removeCoupon() {
    setCouponCode('');
    setAppliedCoupon(null);
    setValidated(false);
    setError('');
    setMessage('Coupon removed.');
  }

  async function validateCart() {
    if (validationLoading || checkoutLoading) return;

    setError('');
    setMessage('');

    if (!shippingAddress.trim() || shippingAddress.trim().length < 5) {
      setError('Please enter a complete shipping address.');
      setValidated(false);
      return;
    }

    if (cart.items.length === 0) {
      setError('Your cart is empty.');
      setValidated(false);
      return;
    }

    try {
      setValidationLoading(true);

      const response = await api.post('/cart/validate');

      if (response.data.valid) {
        setValidated(true);
        setMessage(
          'Cart validated successfully. You can proceed to secure payment.'
        );
      } else {
        setValidated(false);
        setError(
          Array.isArray(response.data.errors)
            ? response.data.errors.join(' ')
            : 'Cart validation failed.'
        );
      }
    } catch (err) {
      setValidated(false);
      setError(
        err.response?.data?.detail || 'Unable to validate cart.'
      );
    } finally {
      setValidationLoading(false);
    }
  }

  async function proceedToPayment() {
    if (!paymentReview || paymentRedirectLoading) return;

    setPaymentRedirectLoading(true);
    setError('');

    try {
      window.location.assign(paymentReview.checkoutUrl);
    } catch (err) {
      setError('Unable to open the secure payment page.');
      setPaymentRedirectLoading(false);
    }
  }

  async function placeOrder() {
    if (checkoutLoading) return;

    setError('');
    setMessage('');

    if (!shippingAddress.trim() || shippingAddress.trim().length < 5) {
      setError('Please enter a complete shipping address.');
      return;
    }

    if (!validated) {
      setError('Please validate your cart before proceeding.');
      return;
    }

    if (cart.items.length === 0) {
      setError('Your cart is empty.');
      return;
    }

    if (couponCode.trim() && !appliedCoupon) {
      setError('Please apply your coupon before proceeding.');
      return;
    }

    if (
      appliedCoupon &&
      Number(appliedCoupon.subtotal) !== Number(cart.total_amount)
    ) {
      setAppliedCoupon(null);
      setValidated(false);
      setError('Cart changed. Please apply your coupon again and validate your cart.');
      return;
    }

    setCheckoutLoading(true);

    let createdOrder = null;

    try {
      const orderItems = cart.items.map((item) => ({
        product_id: item.product_id,
        quantity: item.quantity,
      }));

      // Step 1: Create the order.
      const orderResponse = await api.post('/orders', {
        items: orderItems,
        idempotency_key: crypto.randomUUID(),
        shipping_address: shippingAddress.trim(),
        coupon_code: appliedCoupon?.code || null,
      });

      createdOrder = orderResponse.data;

      if (!createdOrder?.id || !createdOrder?.total_amount) {
        throw new Error(
          'The order was created, but the server did not return its ID or total amount.'
        );
      }

      // Step 2: Ask the backend to create a real Stripe Checkout Session.
      // The backend verifies the order and its total before creating
      // the Stripe session.
      const paymentResponse = await api.post('/payments/checkout', {
        order_id: createdOrder.id,
        amount: Number(createdOrder.total_amount),
        idempotency_key: `order-${createdOrder.id}-stripe-checkout`,
      });

      const checkoutUrl = paymentResponse.data?.checkout_url;

      const paymentId = paymentResponse.data?.payment_id;

        if (!paymentId) {
        throw new Error('Payment ID was not returned by the server.');
        }

        // Save these before leaving for Stripe.
        localStorage.setItem('pending_payment_id', String(paymentId));
        localStorage.setItem('pending_order_id', String(createdOrder.id));

      if (!checkoutUrl) {
        throw new Error(
          'Stripe did not return a Checkout URL. Your order was created, but payment has not started.'
        );
      }

      // Step 3: Clear the cart only after the Stripe session exists.
      try {
        await api.delete('/cart');
      } catch (clearError) {
        console.error(
          'Stripe session created, but cart could not be cleared:',
          clearError
        );
      }

      // Step 4: Redirect to Stripe-hosted Checkout.
      setPaymentReview({
        order: createdOrder,
        checkoutUrl,
      });
    } catch (err) {
      console.error('Stripe checkout error:', err);

      const detail =
        err.response?.data?.detail ||
        err.message ||
        'Unable to start Stripe Checkout.';

      if (createdOrder?.id) {
        setError(
          `Order #${createdOrder.id} was created, but Stripe Checkout could not be started. ${typeof detail === 'string' ? detail : JSON.stringify(detail)}`
        );
        setMessage(
          'Your order exists. Do not place another order until you check this order.'
        );
      } else {
        setError(
          typeof detail === 'string' ? detail : JSON.stringify(detail)
        );
      }

      setValidated(false);
    } finally {
      setCheckoutLoading(false);
    }
  }

  if (loading) {
    return (
      <div className="space-y-6">
        <div>
          <div className="h-8 w-64 animate-pulse rounded bg-slate-200" />
          <div className="mt-3 h-4 w-48 animate-pulse rounded bg-slate-200" />
        </div>
        <CartSkeleton />
      </div>
    );
  }

  return (
    <div className="space-y-7">
      <section className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
        <div className="flex items-center gap-4">
          <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-blue-100 text-blue-700">
            <ShoppingBag size={28} />
          </div>

          <div>
            <h1 className="text-2xl font-extrabold tracking-tight text-slate-900 sm:text-3xl">
              My Shopping Cart
            </h1>
            <p className="mt-1 text-sm text-slate-500">
              Review your selected products before checkout.
            </p>
          </div>
        </div>

        <button
          type="button"
          onClick={() => navigate('/store')}
          className="inline-flex items-center justify-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm font-semibold text-slate-700 transition hover:border-blue-200 hover:bg-blue-50 hover:text-blue-700"
        >
          Continue Shopping
          <ArrowRight size={17} />
        </button>
      </section>

      {error && (
        <div
          role="alert"
          className="flex items-start gap-3 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700"
        >
          <AlertCircle size={20} className="mt-0.5 shrink-0" />
          <span className="flex-1">
            {typeof error === 'string' ? error : JSON.stringify(error)}
          </span>
          <button
            type="button"
            onClick={() => setError('')}
            aria-label="Dismiss error"
          >
            <X size={18} />
          </button>
        </div>
      )}

      {message && (
        <div
          role="status"
          className="flex items-start gap-3 rounded-xl border border-green-200 bg-green-50 p-4 text-sm text-green-800"
        >
          <CheckCircle2 size={20} className="mt-0.5 shrink-0" />
          <span className="flex-1">{message}</span>
          <button
            type="button"
            onClick={() => setMessage('')}
            aria-label="Dismiss message"
          >
            <X size={18} />
          </button>
        </div>
      )}

      {cart.items.length === 0 ? (
        <div className="rounded-3xl border border-slate-200 bg-white px-6 py-16 text-center shadow-sm">
          <div className="mx-auto flex h-24 w-24 items-center justify-center rounded-full bg-blue-50">
            <ShoppingCart size={43} className="text-blue-500" />
          </div>

          <h2 className="mt-6 text-2xl font-bold text-slate-900">
            Your cart is waiting!
          </h2>

          <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-slate-500">
            You haven't added any products yet. Explore our store and
            discover something you'll love.
          </p>

          <button
            type="button"
            onClick={() => navigate('/store')}
            className="mt-7 inline-flex items-center gap-2 rounded-xl bg-blue-600 px-6 py-3 font-semibold text-white shadow-md shadow-blue-100 transition hover:bg-blue-700"
          >
            <ShoppingBag size={18} />
            Explore Store
          </button>
        </div>
      ) : (
        <div className="grid items-start gap-6 lg:grid-cols-3">
          <section className="space-y-4 lg:col-span-2">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-bold text-slate-900">
                Cart Items
                <span className="ml-2 rounded-full bg-blue-100 px-2.5 py-1 text-xs font-bold text-blue-700">
                  {cart.item_count}
                </span>
              </h2>

              <button
                type="button"
                onClick={clearCart}
                disabled={checkoutLoading || clearLoading}
                className="inline-flex items-center gap-1.5 text-sm font-semibold text-red-600 transition hover:text-red-700 disabled:opacity-50"
              >
                {clearLoading ? (
                  <span className="h-4 w-4 animate-spin rounded-full border-2 border-red-300 border-t-red-600" />
                ) : (
                  <Trash2 size={16} />
                )}
                Clear Cart
              </button>
            </div>

            {cart.items.map((item) => {
              const isItemLoading = itemLoading.includes(item.product_id);

              return (
                <article
                  key={item.product_id}
                  className="relative flex flex-col gap-4 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm transition hover:shadow-md sm:flex-row sm:items-center sm:p-5"
                >
                  {isItemLoading && (
                    <div className="absolute inset-0 z-10 flex items-center justify-center rounded-2xl bg-white/60">
                      <span className="h-7 w-7 animate-spin rounded-full border-4 border-blue-200 border-t-blue-600" />
                    </div>
                  )}

                  <div className="flex h-24 w-24 shrink-0 items-center justify-center rounded-xl bg-slate-100 text-slate-400">
                    <Package size={38} />
                  </div>

                  <div className="min-w-0 flex-1">
                    <h3 className="truncate text-base font-bold text-slate-900">
                      {item.name}
                    </h3>

                    <p className="mt-1 text-xs text-slate-500">
                      SKU: {item.sku || 'N/A'}
                    </p>

                    <p className="mt-2 text-sm font-semibold text-slate-700">
                      {formatPrice(item.unit_price)}
                    </p>

                    <p className="mt-1 text-xs text-slate-500">
                      Available stock: {item.available_quantity}
                    </p>

                    <div className="mt-3 inline-flex items-center rounded-lg border border-slate-200 bg-slate-50 p-1">
                      <button
                        type="button"
                        onClick={() =>
                          updateQuantity(item.product_id, item.quantity - 1)
                        }
                        disabled={
                          item.quantity <= 1 ||
                          checkoutLoading ||
                          isItemLoading
                        }
                        aria-label="Decrease quantity"
                        className="rounded-md p-1.5 text-slate-600 transition hover:bg-white hover:text-blue-700 disabled:opacity-30"
                      >
                        <Minus size={15} />
                      </button>

                      <span className="min-w-9 text-center text-sm font-bold text-slate-800">
                        {item.quantity}
                      </span>

                      <button
                        type="button"
                        onClick={() =>
                          updateQuantity(item.product_id, item.quantity + 1)
                        }
                        disabled={
                          item.quantity >= item.available_quantity ||
                          checkoutLoading ||
                          isItemLoading
                        }
                        aria-label="Increase quantity"
                        className="rounded-md p-1.5 text-slate-600 transition hover:bg-white hover:text-blue-700 disabled:opacity-30"
                      >
                        <Plus size={15} />
                      </button>
                    </div>
                  </div>

                  <div className="flex items-center justify-between gap-4 sm:flex-col sm:items-end">
                    <p className="text-lg font-extrabold text-slate-900">
                      {formatPrice(item.line_total)}
                    </p>

                    <button
                      type="button"
                      onClick={() => removeItem(item.product_id)}
                      disabled={checkoutLoading || isItemLoading}
                      className="inline-flex items-center gap-1.5 rounded-lg px-2 py-1.5 text-xs font-semibold text-red-600 transition hover:bg-red-50 disabled:opacity-40"
                    >
                      <Trash2 size={15} />
                      Remove
                    </button>
                  </div>
                </article>
              );
            })}

            <div className="flex items-center gap-2 rounded-xl border border-blue-100 bg-blue-50 p-4 text-xs text-blue-800">
              <ShieldCheck size={18} className="shrink-0" />
              Your order will be checked against current product prices
              and stock before payment.
            </div>
          </section>

          <aside className="h-fit rounded-2xl border border-slate-200 bg-white p-5 shadow-sm lg:sticky lg:top-28 lg:p-6">
            <h2 className="text-xl font-extrabold text-slate-900">
              Order Summary
            </h2>

            <p className="mt-1 text-sm text-slate-500">
              Complete your details to continue to secure payment.
            </p>

            <div className="mt-5">
              <label
                htmlFor="couponCode"
                className="mb-2 block text-sm font-semibold text-slate-700"
              >
                Discount Coupon
              </label>

              <input
                id="couponCode"
                type="text"
                value={couponCode}
                onChange={(event) => {
                  setCouponCode(event.target.value.toUpperCase());
                  setAppliedCoupon(null);
                  setValidated(false);
                  setError('');
                  setMessage('');
                }}
                maxLength={50}
                placeholder="Enter coupon code"
                disabled={checkoutLoading}
                className="w-full rounded-xl border border-slate-200 bg-slate-50 p-3 text-sm uppercase outline-none transition placeholder:normal-case placeholder:text-slate-400 focus:border-blue-400 focus:bg-white focus:ring-4 focus:ring-blue-100 disabled:opacity-60"
              />

              <div className="mt-3 flex gap-2">
                <button
                  type="button"
                  onClick={applyCoupon}
                  disabled={couponLoading || checkoutLoading || !couponCode.trim()}
                  className="flex-1 rounded-xl bg-blue-600 px-4 py-2.5 text-sm font-bold text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {couponLoading ? 'Applying...' : 'Apply Coupon'}
                </button>

                {appliedCoupon && (
                  <button
                    type="button"
                    onClick={removeCoupon}
                    disabled={checkoutLoading}
                    className="rounded-xl border border-red-200 px-4 py-2.5 text-sm font-bold text-red-600 transition hover:bg-red-50 disabled:opacity-50"
                  >
                    Remove
                  </button>
                )}
              </div>

              {appliedCoupon && (
                <p className="mt-2 text-xs font-semibold text-green-600">
                  Coupon {appliedCoupon.code} applied successfully!
                </p>
              )}
            </div>

            <div className="mt-6">
              <label
                htmlFor="shippingAddress"
                className="mb-2 flex items-center gap-2 text-sm font-semibold text-slate-700"
              >
                <MapPin size={17} className="text-blue-600" />
                Shipping Address
              </label>

              <textarea
                id="shippingAddress"
                value={shippingAddress}
                onChange={(event) => {
                  setShippingAddress(event.target.value);
                  setValidated(false);
                }}
                rows={4}
                maxLength={500}
                placeholder="House number, street, city, state and PIN code..."
                disabled={checkoutLoading}
                className="w-full resize-none rounded-xl border border-slate-200 bg-slate-50 p-3 text-sm outline-none transition placeholder:text-slate-400 focus:border-blue-400 focus:bg-white focus:ring-4 focus:ring-blue-100 disabled:opacity-60"
              />

              <p className="mt-1 text-right text-xs text-slate-400">
                {shippingAddress.length}/500
              </p>
            </div>

            <div className="mt-5 space-y-4 border-b border-slate-100 pb-5">
              <div className="flex justify-between text-sm">
                <span className="text-slate-500">Total items</span>
                <span className="font-semibold text-slate-800">
                  {cart.item_count}
                </span>
              </div>

              <div className="flex justify-between text-sm">
                <span className="text-slate-500">Subtotal</span>
                <span className="font-semibold text-slate-800">
                  {formatPrice(appliedCoupon?.subtotal ?? cart.total_amount)}
                </span>
              </div>

              {appliedCoupon ? (
                <>
                  <div className="flex justify-between text-sm">
                    <span className="text-slate-500">Tax</span>
                    <span className="font-semibold text-slate-800">
                      {formatPrice(appliedCoupon.tax_amount)}
                    </span>
                  </div>

                  <div className="flex justify-between text-sm">
                    <span className="text-slate-500">Coupon discount</span>
                    <span className="font-semibold text-green-600">
                      -{formatPrice(appliedCoupon.discount_amount)}
                    </span>
                  </div>

                  <div className="flex justify-between text-sm">
                    <span className="text-slate-500">Shipping</span>
                    <span className="font-semibold text-slate-800">
                      {formatPrice(appliedCoupon.shipping_amount)}
                    </span>
                  </div>
                </>
              ) : (
                <div className="flex justify-between text-sm">
                  <span className="text-slate-500">Shipping</span>
                  <span className="font-semibold text-green-600">
                    Calculated at checkout
                  </span>
                </div>
              )}
            </div>

            <div className="flex items-center justify-between py-5">
              <span className="text-base font-bold text-slate-900">
                Cart Total
              </span>
              <span className="text-2xl font-extrabold text-blue-700">
                {formatPrice(appliedCoupon?.total_amount ?? cart.total_amount)}
              </span>
            </div>

            <button
              type="button"
              onClick={validateCart}
              disabled={
                checkoutLoading ||
                validationLoading ||
                itemLoading.length > 0
              }
              className="flex w-full items-center justify-center gap-2 rounded-xl border border-blue-200 bg-blue-50 px-4 py-3 text-sm font-bold text-blue-700 transition hover:bg-blue-100 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {validationLoading ? (
                <>
                  <span className="h-4 w-4 animate-spin rounded-full border-2 border-blue-300 border-t-blue-700" />
                  Validating...
                </>
              ) : validated ? (
                <>
                  <CheckCircle2 size={18} />
                  Cart Validated
                </>
              ) : (
                <>
                  <RefreshCw size={17} />
                  Validate Cart
                </>
              )}
            </button>

            <button
              type="button"
              onClick={placeOrder}
              disabled={
                !validated ||
                checkoutLoading ||
                validationLoading ||
                itemLoading.length > 0
              }
              className="mt-3 flex w-full items-center justify-center gap-2 rounded-xl bg-blue-600 px-4 py-3.5 text-sm font-bold text-white shadow-md shadow-blue-100 transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50 disabled:shadow-none"
            >
              {checkoutLoading ? (
                <>
                  <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/40 border-t-white" />
                  Connecting to Stripe...
                </>
              ) : (
                <>
                  <CreditCard size={18} />
                  Pay Securely with Stripe
                  <ArrowRight size={18} />
                </>
              )}
            </button>

            <p className="mt-4 text-center text-xs leading-5 text-slate-400">
              Secure payment powered by Stripe. Your payment is confirmed
              by our payment server after Stripe verifies it.
            </p>
          </aside>
        </div>

      )}

      {paymentReview && (
        <div className="fixed inset-0 z-50 flex items-center justify-center overflow-y-auto bg-slate-950/60 p-4">
          <div className="my-auto w-full max-w-2xl rounded-2xl bg-white p-6 shadow-2xl sm:p-8">
            <div className="mb-6 flex items-center gap-3">
              <div className="rounded-xl bg-blue-100 p-3 text-blue-700">
                <CreditCard size={24} />
              </div>
              <div>
                <h2 className="text-xl font-extrabold text-slate-900">
                  Review Your Payment
                </h2>
                <p className="text-sm text-slate-500">
                  Order #{paymentReview.order.id}
                </p>
              </div>
            </div>

            <div className="mb-6 rounded-xl border border-slate-200 p-4">
              <h3 className="mb-3 font-bold text-slate-800">
                Order Items
              </h3>

              <div className="space-y-3">
                {paymentReview.order.items?.map((item) => (
                  <div
                    key={item.id}
                    className="flex items-center justify-between gap-4 text-sm"
                  >
                    <div>
                      <p className="font-semibold text-slate-800">
                        {item.product_name}
                      </p>
                      <p className="text-slate-500">
                        {formatPrice(item.unit_price)} × {item.quantity}
                      </p>
                    </div>
                    <span className="font-bold text-slate-800">
                      {formatPrice(item.line_subtotal)}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            <div className="space-y-3 border-b border-slate-200 pb-5">
              <div className="flex justify-between text-sm">
                <span className="text-slate-500">Subtotal</span>
                <span className="font-semibold text-slate-800">
                  {formatPrice(paymentReview.order.subtotal)}
                </span>
              </div>

              <div className="flex justify-between text-sm">
                <span className="text-slate-500">Tax</span>
                <span className="font-semibold text-slate-800">
                  {formatPrice(paymentReview.order.tax_amount)}
                </span>
              </div>

              {Number(paymentReview.order.discount_amount) > 0 && (
                <div className="flex justify-between text-sm">
                  <span className="text-slate-500">
                    Coupon discount
                    {paymentReview.order.coupon_code
                      ? ` (${paymentReview.order.coupon_code})`
                      : ''}
                  </span>
                  <span className="font-semibold text-green-600">
                    -{formatPrice(paymentReview.order.discount_amount)}
                  </span>
                </div>
              )}

              <div className="flex justify-between text-sm">
                <span className="text-slate-500">Shipping</span>
                <span className="font-semibold text-slate-800">
                  {Number(paymentReview.order.shipping_amount) === 0
                    ? 'Free'
                    : formatPrice(paymentReview.order.shipping_amount)}
                </span>
              </div>
            </div>

            <div className="flex items-center justify-between py-5">
              <span className="font-bold text-slate-900">
                Total Payable
              </span>
              <span className="text-2xl font-extrabold text-blue-700">
                {formatPrice(paymentReview.order.total_amount)}
              </span>
            </div>

            <button
              type="button"
              onClick={proceedToPayment}
              disabled={paymentRedirectLoading}
              className="flex w-full items-center justify-center gap-2 rounded-xl bg-blue-600 px-5 py-3.5 font-bold text-white transition hover:bg-blue-700 disabled:opacity-50"
            >
              <ShieldCheck size={19} />
              {paymentRedirectLoading
                ? 'Opening Secure Payment...'
                : 'Proceed to Secure Payment'}
              <ArrowRight size={18} />
            </button>

            <p className="mt-4 text-center text-xs text-slate-500">
              Please verify your order and total before proceeding.
              Your payment will be securely processed by Stripe.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
