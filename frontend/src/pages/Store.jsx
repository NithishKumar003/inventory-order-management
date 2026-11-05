import { useEffect, useState } from 'react';
import {
  ShoppingCart,
  Search,
  Package,
  Heart,
  X,
  CheckCircle2,
  AlertCircle,
  RefreshCw,
} from 'lucide-react';
import api from '../services/api';

function ProductSkeleton() {
  return (
    <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
      <div className="h-52 animate-pulse bg-slate-200" />
      <div className="space-y-4 p-5">
        <div className="h-3 w-20 animate-pulse rounded bg-slate-200" />
        <div className="h-5 w-3/4 animate-pulse rounded bg-slate-200" />
        <div className="h-4 w-1/2 animate-pulse rounded bg-slate-200" />
        <div className="h-7 w-24 animate-pulse rounded bg-slate-200" />
        <div className="h-11 animate-pulse rounded-xl bg-slate-200" />
      </div>
    </div>
  );
}

export default function Store() {
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [wishlistIds, setWishlistIds] = useState([]);
  const [cartLoading, setCartLoading] = useState([]);
  const [wishlistLoading, setWishlistLoading] = useState([]);
  const [failedImages, setFailedImages] = useState([]);

  async function fetchProducts() {
    try {
      setLoading(true);
      setError('');

      const response = await api.get('/products');
      setProducts(Array.isArray(response.data) ? response.data : []);
    } catch (err) {
      setError(
        err.response?.data?.detail || 'Unable to load products.'
      );
    } finally {
      setLoading(false);
    }
  }

  async function fetchWishlist() {
    try {
      const response = await api.get('/wishlist');

      const ids = (response.data || []).map(
        (item) => item.product_id
      );

      setWishlistIds(ids);
    } catch (err) {
      console.error('Unable to load wishlist:', err);
    }
  }

  useEffect(() => {
    fetchProducts();
    fetchWishlist();
  }, []);

  function showMessage(text) {
    setMessage(text);
    setError('');
  }

  async function addToCart(productId) {
    if (cartLoading.includes(productId)) return;

    try {
      setCartLoading((previous) => [...previous, productId]);
      setMessage('');
      setError('');

      await api.post('/cart/items', {
        product_id: productId,
        quantity: 1,
      });

      showMessage('Product added to your cart successfully.');
    } catch (err) {
      setError(
        err.response?.data?.detail || 'Unable to add product to cart.'
      );
    } finally {
      setCartLoading((previous) =>
        previous.filter((id) => id !== productId)
      );
    }
  }

  async function toggleWishlist(productId) {
    if (wishlistLoading.includes(productId)) return;

    try {
      setWishlistLoading((previous) => [...previous, productId]);
      setMessage('');
      setError('');

      if (wishlistIds.includes(productId)) {
        await api.delete(`/wishlist/items/${productId}`);

        setWishlistIds((previous) =>
          previous.filter((id) => id !== productId)
        );

        showMessage('Product removed from your wishlist.');
      } else {
        await api.post('/wishlist/items', {
          product_id: productId,
        });

        setWishlistIds((previous) => [...previous, productId]);

        showMessage('Product added to your wishlist.');
      }
    } catch (err) {
      setError(
        err.response?.data?.detail || 'Unable to update wishlist.'
      );
    } finally {
      setWishlistLoading((previous) =>
        previous.filter((id) => id !== productId)
      );
    }
  }

  const searchText = search.trim().toLowerCase();

  const filteredProducts = products.filter((product) => {
    const name = String(product.name || '').toLowerCase();
    const category = String(product.category || '').toLowerCase();
    const sku = String(product.sku || '').toLowerCase();
    const brand = String(product.brand || '').toLowerCase();

    return (
      name.includes(searchText) ||
      category.includes(searchText) ||
      sku.includes(searchText) ||
      brand.includes(searchText)
    );
  });

  return (
    <div className="space-y-7">
      {/* Store Welcome Section */}
      <section className="relative overflow-hidden rounded-3xl bg-gradient-to-r from-blue-700 via-blue-600 to-indigo-600 px-6 py-10 text-white shadow-lg shadow-blue-200 sm:px-10">
        <div className="relative z-10 max-w-2xl">
          <span className="inline-flex items-center rounded-full border border-white/20 bg-white/10 px-3 py-1 text-xs font-semibold uppercase tracking-wider">
            StockFlow Marketplace
          </span>

          <h1 className="mt-5 text-3xl font-extrabold tracking-tight sm:text-4xl">
            Discover products you'll love.
          </h1>

          <p className="mt-3 max-w-lg text-sm leading-6 text-blue-100 sm:text-base">
            Explore our collection, save your favourites, and enjoy a
            simple shopping experience.
          </p>

          <div className="mt-6 flex flex-wrap items-center gap-3 text-sm">
            <span className="rounded-xl bg-white/15 px-4 py-2 font-semibold">
              {products.length} Products
            </span>
            <span className="rounded-xl bg-white/15 px-4 py-2">
              Easy Shopping
            </span>
          </div>
        </div>

        <div className="pointer-events-none absolute -right-12 -top-16 h-72 w-72 rounded-full border-[35px] border-white/10" />
        <div className="pointer-events-none absolute -bottom-32 right-32 h-64 w-64 rounded-full bg-white/10 blur-2xl" />
      </section>

      {/* Notifications */}
      {message && (
        <div
          role="status"
          className="flex items-center gap-3 rounded-xl border border-green-200 bg-green-50 p-4 text-sm font-medium text-green-800"
        >
          <CheckCircle2 size={20} className="shrink-0" />
          <span className="flex-1">{message}</span>
          <button
            type="button"
            onClick={() => setMessage('')}
            aria-label="Dismiss notification"
          >
            <X size={18} />
          </button>
        </div>
      )}

      {error && (
        <div
          role="alert"
          className="flex items-center gap-3 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700"
        >
          <AlertCircle size={20} className="shrink-0" />
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

      {/* Search and Product Count */}
      <section className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
        <div>
          <h2 className="text-2xl font-bold text-slate-900">
            Explore Products
          </h2>
          <p className="mt-1 text-sm text-slate-500">
            Find something you need today.
          </p>
        </div>

        <div className="flex w-full items-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-3 shadow-sm transition focus-within:border-blue-400 focus-within:ring-4 focus-within:ring-blue-100 sm:max-w-sm">
          <Search size={19} className="shrink-0 text-slate-400" />

          <input
            type="text"
            placeholder="Search name, brand, category or SKU..."
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            className="min-w-0 flex-1 bg-transparent text-sm outline-none placeholder:text-slate-400"
          />

          {search && (
            <button
              type="button"
              onClick={() => setSearch('')}
              aria-label="Clear search"
              className="text-slate-400 hover:text-slate-700"
            >
              <X size={18} />
            </button>
          )}
        </div>
      </section>

      {/* Product Results */}
      <section>
        {loading ? (
          <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {Array.from({ length: 8 }).map((_, index) => (
              <ProductSkeleton key={index} />
            ))}
          </div>
        ) : error && products.length === 0 ? (
          <div className="rounded-2xl border border-slate-200 bg-white px-6 py-12 text-center shadow-sm">
            <AlertCircle size={42} className="mx-auto text-red-400" />

            <h3 className="mt-4 text-lg font-bold text-slate-800">
              Products could not be loaded
            </h3>

            <p className="mt-2 text-sm text-slate-500">
              Please check your connection and try again.
            </p>

            <button
              type="button"
              onClick={fetchProducts}
              className="mt-5 inline-flex items-center gap-2 rounded-xl bg-blue-600 px-5 py-3 text-sm font-semibold text-white hover:bg-blue-700"
            >
              <RefreshCw size={17} />
              Try Again
            </button>
          </div>
        ) : filteredProducts.length === 0 ? (
          <div className="rounded-2xl border border-slate-200 bg-white px-6 py-16 text-center shadow-sm">
            <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl bg-slate-100">
              <Package size={34} className="text-slate-400" />
            </div>

            <h3 className="mt-5 text-lg font-bold text-slate-800">
              {search ? 'No products found' : 'No products available'}
            </h3>

            <p className="mt-2 text-sm text-slate-500">
              {search
                ? 'Try a different product name, brand, category or SKU.'
                : 'Please check back later for available products.'}
            </p>

            {search && (
              <button
                type="button"
                onClick={() => setSearch('')}
                className="mt-5 rounded-xl bg-blue-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-blue-700"
              >
                Clear Search
              </button>
            )}
          </div>
        ) : (
          <>
            <div className="mb-4 flex items-center justify-between">
              <p className="text-sm text-slate-500">
                Showing{' '}
                <span className="font-semibold text-slate-800">
                  {filteredProducts.length}
                </span>{' '}
                products
              </p>
            </div>

            <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
              {filteredProducts.map((product) => {
                const isWishlisted = wishlistIds.includes(product.id);
                const isCartLoading = cartLoading.includes(product.id);
                const isWishlistLoading = wishlistLoading.includes(product.id);
                const imageFailed = failedImages.includes(product.id);

                return (
                  <article
                    key={product.id}
                    className="group overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm transition-all duration-300 hover:-translate-y-1 hover:border-blue-200 hover:shadow-xl hover:shadow-slate-200/70"
                  >
                    {/* Product Image */}
                    <div className="relative flex h-52 items-center justify-center overflow-hidden bg-slate-50">
                      {product.image_url && !imageFailed ? (
                        <img
                          src={product.image_url}
                          alt={product.name}
                          loading="lazy"
                          onError={() =>
                            setFailedImages((previous) =>
                              previous.includes(product.id)
                                ? previous
                                : [...previous, product.id]
                            )
                          }
                          className="h-full w-full object-contain p-5 transition-transform duration-500 group-hover:scale-110"
                        />
                      ) : (
                        <div className="flex h-20 w-20 items-center justify-center rounded-2xl bg-white shadow-sm">
                          <Package size={42} className="text-slate-300" />
                        </div>
                      )}

                      <span className="absolute left-3 top-3 rounded-lg bg-white/90 px-3 py-1 text-xs font-semibold text-slate-600 shadow-sm">
                        {product.category || 'General'}
                      </span>

                      <button
                        type="button"
                        onClick={() => toggleWishlist(product.id)}
                        disabled={isWishlistLoading}
                        title={
                          isWishlisted
                            ? 'Remove from wishlist'
                            : 'Add to wishlist'
                        }
                        aria-label={
                          isWishlisted
                            ? 'Remove from wishlist'
                            : 'Add to wishlist'
                        }
                        className={`absolute right-3 top-3 flex h-10 w-10 items-center justify-center rounded-full bg-white shadow-md transition hover:scale-110 disabled:opacity-60 ${
                          isWishlisted
                            ? 'text-red-500'
                            : 'text-slate-500 hover:text-red-500'
                        }`}
                      >
                        <Heart
                          size={20}
                          className={isWishlisted ? 'fill-red-500' : ''}
                        />
                      </button>
                    </div>

                    {/* Product Information */}
                    <div className="p-5">
                      <p className="text-xs font-semibold uppercase tracking-wider text-blue-600">
                        SKU: {product.sku || 'N/A'}
                      </p>

                      <h3 className="mt-2 line-clamp-2 min-h-12 text-base font-bold text-slate-900 transition-colors group-hover:text-blue-700">
                        {product.name}
                      </h3>

                      {product.brand && (
                        <p className="mt-1 truncate text-sm text-slate-500">
                          {product.brand}
                        </p>
                      )}

                      <div className="mt-4 flex items-center justify-between">
                        <div>
                          <p className="text-xs text-slate-400">Price</p>
                          <p className="text-xl font-extrabold text-slate-900">
                            ₹{Number(product.price).toLocaleString('en-IN', {
                              minimumFractionDigits: 2,
                              maximumFractionDigits: 2,
                            })}
                          </p>
                        </div>
                      </div>

                      <button
                        type="button"
                        onClick={() => addToCart(product.id)}
                        disabled={isCartLoading}
                        className="mt-5 flex w-full items-center justify-center gap-2 rounded-xl bg-blue-600 px-4 py-3 text-sm font-bold text-white shadow-sm shadow-blue-100 transition hover:bg-blue-700 hover:shadow-md disabled:cursor-not-allowed disabled:opacity-60"
                      >
                        {isCartLoading ? (
                          <>
                            <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/40 border-t-white" />
                            Adding...
                          </>
                        ) : (
                          <>
                            <ShoppingCart size={18} />
                            Add to Cart
                          </>
                        )}
                      </button>
                    </div>
                  </article>
                );
              })}
            </div>
          </>
        )}
      </section>
    </div>
  );
}