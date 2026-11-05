import { useEffect, useState } from 'react';
import {
  Heart,
  ShoppingCart,
  Trash2,
  Package,
  ArrowRight,
  AlertCircle,
  CheckCircle2,
  RefreshCw,
  X,
  Sparkles,
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import api from '../services/api';

function formatPrice(value) {
  return `₹${Number(value || 0).toLocaleString('en-IN', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

function WishlistSkeleton() {
  return (
    <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
      {[1, 2, 3].map((item) => (
        <div
          key={item}
          className="animate-pulse rounded-2xl border border-slate-200 bg-white p-4"
        >
          <div className="h-48 rounded-xl bg-slate-200" />
          <div className="mt-5 h-5 w-3/4 rounded bg-slate-200" />
          <div className="mt-3 h-4 w-1/2 rounded bg-slate-200" />
          <div className="mt-5 h-7 w-1/3 rounded bg-slate-200" />
          <div className="mt-5 h-10 rounded-lg bg-slate-200" />
        </div>
      ))}
    </div>
  );
}

export default function Wishlist() {
  const navigate = useNavigate();

  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [itemLoading, setItemLoading] = useState([]);

  async function fetchWishlist() {
    try {
      setLoading(true);
      setError('');

      const wishlistResponse = await api.get('/wishlist');
      const wishlistRecords = Array.isArray(wishlistResponse.data)
        ? wishlistResponse.data
        : [];

      const productResults = await Promise.all(
        wishlistRecords.map(async (wishlistItem) => {
          try {
            const productResponse = await api.get(
              `/products/${wishlistItem.product_id}`
            );

            return {
              ...wishlistItem,
              ...productResponse.data,
            };
          } catch (productError) {
            console.error(
              `Unable to load product ${wishlistItem.product_id}:`,
              productError
            );

            return {
              ...wishlistItem,
              unavailable: true,
            };
          }
        })
      );

      setItems(productResults);
    } catch (err) {
      setError(
        err.response?.data?.detail || 'Unable to load wishlist.'
      );
    } finally {
      setLoading(false);
    }
  }

  async function removeItem(productId) {
    if (itemLoading.includes(productId)) return;

    try {
      setItemLoading((previous) => [...previous, productId]);
      setError('');
      setMessage('');

      await api.delete(`/wishlist/items/${productId}`);

      setItems((previous) =>
        previous.filter((item) => item.product_id !== productId)
      );

      setMessage('Product removed from your wishlist.');
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

  async function moveToCart(productId) {
    if (itemLoading.includes(productId)) return;

    try {
      setItemLoading((previous) => [...previous, productId]);
      setError('');
      setMessage('');

      await api.post(`/wishlist/items/${productId}/move-to-cart`);

      setItems((previous) =>
        previous.filter((item) => item.product_id !== productId)
      );

      setMessage('Product successfully moved to your cart.');
    } catch (err) {
      setError(
        err.response?.data?.detail ||
          'Unable to move product to cart.'
      );
    } finally {
      setItemLoading((previous) =>
        previous.filter((id) => id !== productId)
      );
    }
  }

  useEffect(() => {
    fetchWishlist();
  }, []);

  if (loading) {
    return (
      <div className="space-y-6">
        <div>
          <div className="h-8 w-52 animate-pulse rounded bg-slate-200" />
          <div className="mt-3 h-4 w-64 animate-pulse rounded bg-slate-200" />
        </div>
        <WishlistSkeleton />
      </div>
    );
  }

  return (
    <div className="space-y-7">
      {/* Heading */}
      <section className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
        <div className="flex items-center gap-4">
          <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-pink-100 text-pink-600">
            <Heart size={28} />
          </div>

          <div>
            <h1 className="text-2xl font-extrabold tracking-tight text-slate-900 sm:text-3xl">
              My Wishlist
            </h1>
            <p className="mt-1 text-sm text-slate-500">
              Your favourite products, saved for later.
            </p>
          </div>
        </div>

        <button
          type="button"
          onClick={() => navigate('/store')}
          className="inline-flex items-center justify-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm font-semibold text-slate-700 transition hover:border-blue-200 hover:bg-blue-50 hover:text-blue-700"
        >
          Explore Store
          <ArrowRight size={17} />
        </button>
      </section>

      {/* Notifications */}
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

      {message && (
        <div
          role="status"
          className="flex items-start gap-3 rounded-xl border border-green-200 bg-green-50 p-4 text-sm text-green-800"
        >
          <CheckCircle2 size={19} className="mt-0.5 shrink-0" />
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

      {/* Wishlist Count */}
      {items.length > 0 && (
        <div className="flex items-center justify-between rounded-xl border border-pink-100 bg-gradient-to-r from-pink-50 to-white p-4">
          <div className="flex items-center gap-3">
            <Heart size={20} className="fill-pink-500 text-pink-500" />
            <div>
              <p className="text-sm font-bold text-slate-900">
                Saved Products
              </p>
              <p className="text-xs text-slate-500">
                Products you may want to purchase.
              </p>
            </div>
          </div>

          <span className="rounded-full bg-pink-100 px-3 py-1.5 text-sm font-bold text-pink-700">
            {items.length} {items.length === 1 ? 'Item' : 'Items'}
          </span>
        </div>
      )}

      {/* Empty State */}
      {items.length === 0 ? (
        <div className="rounded-3xl border border-dashed border-slate-300 bg-white px-6 py-16 text-center">
          <div className="mx-auto flex h-24 w-24 items-center justify-center rounded-full bg-pink-50">
            <Heart size={43} className="text-pink-400" />
          </div>

          <h2 className="mt-6 text-2xl font-bold text-slate-900">
            Your wishlist is empty
          </h2>

          <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-slate-500">
            Save products you love and keep them all in one place.
            You can move them to your cart whenever you're ready.
          </p>

          <button
            type="button"
            onClick={() => navigate('/store')}
            className="mt-7 inline-flex items-center gap-2 rounded-xl bg-blue-600 px-6 py-3 font-semibold text-white shadow-md shadow-blue-100 transition hover:bg-blue-700"
          >
            <ShoppingCart size={18} />
            Browse Products
          </button>
        </div>
      ) : (
        <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {items.map((item) => {
            const isItemLoading = itemLoading.includes(item.product_id);

            return (
              <article
                key={item.product_id}
                className="group relative overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm transition duration-300 hover:-translate-y-1 hover:shadow-xl"
              >
                {/* Product Image */}
                <div className="relative flex h-52 items-center justify-center overflow-hidden bg-slate-50 p-5">
                  {item.image_url ? (
                    <img
                      src={item.image_url}
                      alt={item.name || 'Product'}
                      loading="lazy"
                      onError={(event) => {
                        event.currentTarget.style.display = 'none';
                      }}
                      className="h-full w-full object-contain transition duration-500 group-hover:scale-105"
                    />
                  ) : (
                    <Package size={55} className="text-slate-300" />
                  )}

                  <div className="absolute left-3 top-3 flex items-center gap-1 rounded-full bg-white/90 px-3 py-1.5 text-xs font-semibold text-pink-600 shadow-sm">
                    <Heart size={13} className="fill-pink-500" />
                    Saved
                  </div>

                  <button
                    type="button"
                    onClick={() => removeItem(item.product_id)}
                    disabled={isItemLoading}
                    aria-label="Remove from wishlist"
                    className="absolute right-3 top-3 flex h-9 w-9 items-center justify-center rounded-full bg-white text-red-500 shadow-sm transition hover:bg-red-50 hover:text-red-700 disabled:opacity-40"
                  >
                    <Trash2 size={17} />
                  </button>
                </div>

                {/* Product Information */}
                <div className="p-5">
                  {item.unavailable ? (
                    <div>
                      <h3 className="font-bold text-slate-800">
                        Product unavailable
                      </h3>
                      <p className="mt-2 text-sm text-slate-500">
                        Product ID: {item.product_id}
                      </p>
                      <p className="mt-2 text-xs text-amber-600">
                        Product details could not be loaded.
                      </p>
                    </div>
                  ) : (
                    <>
                      <h3 className="line-clamp-2 min-h-12 text-base font-bold text-slate-900">
                        {item.name}
                      </h3>

                      <p className="mt-1 text-xs text-slate-500">
                        SKU: {item.sku || 'N/A'}
                      </p>

                      {item.brand && (
                        <p className="mt-1 text-xs text-slate-500">
                          Brand: {item.brand}
                        </p>
                      )}

                      <div className="mt-4 flex items-center justify-between">
                        <p className="text-xl font-extrabold text-slate-900">
                          {formatPrice(item.price)}
                        </p>

                        <span className="flex items-center gap-1 text-xs font-semibold text-amber-500">
                          <Sparkles size={14} />
                          Favourite
                        </span>
                      </div>
                    </>
                  )}

                  {/* Actions */}
                  <div className="mt-5 flex gap-2">
                    <button
                      type="button"
                      onClick={() => moveToCart(item.product_id)}
                      disabled={item.unavailable || isItemLoading}
                      className="flex flex-1 items-center justify-center gap-2 rounded-xl bg-blue-600 px-3 py-3 text-sm font-bold text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      {isItemLoading ? (
                        <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/40 border-t-white" />
                      ) : (
                        <ShoppingCart size={17} />
                      )}
                      {isItemLoading ? 'Processing...' : 'Move to Cart'}
                    </button>

                    <button
                      type="button"
                      onClick={() => removeItem(item.product_id)}
                      disabled={isItemLoading}
                      aria-label="Remove product"
                      title="Remove from wishlist"
                      className="flex h-11 w-11 items-center justify-center rounded-xl border border-slate-200 text-red-500 transition hover:border-red-200 hover:bg-red-50 disabled:opacity-40"
                    >
                      <Trash2 size={17} />
                    </button>
                  </div>
                </div>

                {isItemLoading && (
                  <div className="absolute inset-0 z-20 flex items-center justify-center bg-white/50 backdrop-blur-[1px]">
                    <span className="h-8 w-8 animate-spin rounded-full border-4 border-blue-200 border-t-blue-600" />
                  </div>
                )}
              </article>
            );
          })}
        </div>
      )}

      {/* Footer note */}
      {items.length > 0 && (
        <div className="flex items-center gap-2 rounded-xl bg-slate-100 p-4 text-xs text-slate-600">
          <Heart size={16} className="shrink-0 text-pink-500" />
          Your saved products stay here until you remove them or move them
          to your cart.
        </div>
      )}
    </div>
  );
}