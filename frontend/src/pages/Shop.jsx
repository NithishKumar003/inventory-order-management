import { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';

import {
  ShoppingCart,
  Search,
  Package,
  Heart,
  X,
  CheckCircle2,
  AlertCircle,
  RefreshCw,
  Star,
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

function RatingStars({ rating = 0, size = 16 }) {
  return (
    <div className="flex items-center gap-0.5">
      {[1, 2, 3, 4, 5].map((star) => (
        <Star
          key={star}
          size={size}
          className={
            star <= Math.round(Number(rating) || 0)
              ? 'fill-yellow-400 text-yellow-400'
              : 'text-slate-300'
          }
        />
      ))}
    </div>
  );
}

export default function Store() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const categoryFilter = searchParams.get('category') || '';
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');

  const [currentPage, setCurrentPage] = useState(1);
  const [totalProducts, setTotalProducts] = useState(0);

  const productsPerPage = 8;
  const totalPages = Math.ceil(totalProducts / productsPerPage);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  const [wishlistIds, setWishlistIds] = useState([]);
  const [cartLoading, setCartLoading] = useState([]);
  const [wishlistLoading, setWishlistLoading] = useState([]);
  const [failedImages, setFailedImages] = useState([]);

  const [ratingSummaries, setRatingSummaries] = useState({});
  const [ratingLoading, setRatingLoading] = useState(true);

  const [expandedProductId, setExpandedProductId] = useState(null);
  const [productReviews, setProductReviews] = useState({});
  const [reviewsLoadingIds, setReviewsLoadingIds] = useState([]);
  const [reviewsErrors, setReviewsErrors] = useState({});

  async function fetchRatingSummaries(productList) {
    setRatingLoading(true);

    const results = await Promise.all(
      productList.map(async (product) => {
        try {
          const response = await api.get(
            `/reviews/products/${product.id}/rating-summary`
          );

          return {
            id: product.id,
            data: response.data,
            failed: false,
          };
        } catch (err) {
          console.error(
            `Rating summary failed for product ${product.id}:`,
            err.response?.status,
            err.response?.data || err.message
          );

          return {
            id: product.id,
            data: null,
            failed: true,
          };
        }
      })
    );

    const summaries = {};

    results.forEach((result) => {
      summaries[result.id] = result.failed
        ? null
        : result.data;
    });

    setRatingSummaries(summaries);
    setRatingLoading(false);
  }

async function fetchProducts(page = currentPage, searchTerm = search) {
  try {
    setLoading(true);
    setError('');

    const skip = (page - 1) * productsPerPage;

    const response = await api.get('/products/paginated', {
      params: {
        skip,
        limit: productsPerPage,
        search: searchTerm.trim() || undefined,
        category: categoryFilter || undefined,
      },
    });

    const productList = response.data.items || [];

    setProducts(productList);
    setTotalProducts(response.data.total || 0);

    // Fetch ratings for products on the current page.
    fetchRatingSummaries(productList);
  } catch (err) {
    console.error('Unable to load products:', err);

    setError(
      err.response?.data?.detail || 'Unable to load products.'
    );
    setRatingLoading(false);
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

  async function loadProductReviews(productId) {
    try {
      setReviewsLoadingIds((previous) =>
        previous.includes(productId)
          ? previous
          : [...previous, productId]
      );

      setReviewsErrors((previous) => ({
        ...previous,
        [productId]: '',
      }));

      const response = await api.get(
        `/reviews/products/${productId}/reviews`
      );

      setProductReviews((previous) => ({
        ...previous,
        [productId]: Array.isArray(response.data)
          ? response.data
          : [],
      }));
    } catch (err) {
      console.error(
        `Unable to load reviews for product ${productId}:`,
        err.response?.status,
        err.response?.data || err.message
      );

      setReviewsErrors((previous) => ({
        ...previous,
        [productId]: 'Unable to load customer reviews. Please try again.',
      }));
    } finally {
      setReviewsLoadingIds((previous) =>
        previous.filter((id) => id !== productId)
      );
    }
  }

  async function toggleProductReviews(productId) {
    if (expandedProductId === productId) {
      setExpandedProductId(null);
      return;
    }

    setExpandedProductId(productId);

    const alreadyLoaded = Object.prototype.hasOwnProperty.call(
      productReviews,
      productId
    );

    if (!alreadyLoaded) {
      await loadProductReviews(productId);
    }
  }

  useEffect(() => {
    fetchProducts(currentPage, search);
  }, [currentPage, search, categoryFilter]);

  useEffect(() => {
    fetchWishlist();
  }, []);

  function handleSearchChange(value) {
    setSearch(value);
    setCurrentPage(1);
  }

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

  const filteredProducts = products;

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

      {/* Search */}
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
            onChange={(event) => handleSearchChange(event.target.value)}
            className="min-w-0 flex-1 bg-transparent text-sm outline-none placeholder:text-slate-400"
          />

          {search && (
            <button
              type="button"
              onClick={() => handleSearchChange('')}
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
                  {totalProducts === 0
                    ? 0
                    : (currentPage - 1) * productsPerPage + 1}
                  {'–'}
                  {Math.min(currentPage * productsPerPage, totalProducts)}
                </span>{' '}
                of{' '}
                <span className="font-semibold text-slate-800">
                  {totalProducts}
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

                const summary = ratingSummaries[product.id];
                const ratingUnavailable =
                  !ratingLoading &&
                  Object.prototype.hasOwnProperty.call(
                    ratingSummaries,
                    product.id
                  ) &&
                  summary === null;

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

                      <button
                        type="button"
                        onClick={() => navigate(`/products/${product.id}`)}
                        className="mt-3 w-full rounded-xl border border-blue-200 px-4 py-2.5 text-sm font-semibold text-blue-700 transition hover:bg-blue-50"
                      >
                        View Product Details
                      </button>

                      {product.brand && (
                        <p className="mt-1 truncate text-sm text-slate-500">
                          {product.brand}
                        </p>
                      )}

                      {/* Customer Rating */}
                      <div className="mt-3 flex min-h-6 flex-wrap items-center gap-2">
                        {ratingLoading ? (
                          <span className="text-xs text-slate-400">
                            Loading rating...
                          </span>
                        ) : ratingUnavailable ? (
                          <span className="text-xs text-slate-400">
                            Rating unavailable
                          </span>
                        ) : (
                          <>
                            <RatingStars
                              rating={summary?.average_rating || 0}
                            />

                            <span className="text-sm font-bold text-slate-700">
                              {summary?.total_reviews > 0
                                ? Number(summary.average_rating).toFixed(1)
                                : 'No ratings'}
                            </span>

                            <span className="text-xs text-slate-500">
                              ({summary?.total_reviews || 0} reviews)
                            </span>
                          </>
                        )}
                      </div>

                      {/* Price */}
                      <div className="mt-4">
                        <p className="text-xs text-slate-400">Price</p>
                        <p className="text-xl font-extrabold text-slate-900">
                          ₹
                          {Number(product.price).toLocaleString('en-IN', {
                            minimumFractionDigits: 2,
                            maximumFractionDigits: 2,
                          })}
                        </p>
                      </div>

                      {/* View Customer Reviews */}
                      <button
                        type="button"
                        onClick={() => toggleProductReviews(product.id)}
                        className="mt-4 flex w-full items-center justify-center rounded-xl border border-blue-200 px-4 py-2.5 text-sm font-semibold text-blue-700 transition hover:bg-blue-50"
                      >
                        {expandedProductId === product.id
                          ? 'Hide Reviews'
                          : 'View Customer Reviews'}
                      </button>

                      {/* Add to Cart */}
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

                    {/* Customer Reviews List */}
                    {expandedProductId === product.id && (
                      <div className="border-t border-slate-100 bg-slate-50 p-5">
                        <h4 className="font-bold text-slate-900">
                          Customer Reviews
                        </h4>

                        {reviewsLoadingIds.includes(product.id) ? (
                          <p className="mt-3 text-sm text-slate-500">
                            Loading reviews...
                          </p>
                        ) : reviewsErrors[product.id] ? (
                          <div className="mt-3">
                            <p className="text-sm text-red-600">
                              {reviewsErrors[product.id]}
                            </p>

                            <button
                              type="button"
                              onClick={() => loadProductReviews(product.id)}
                              className="mt-2 text-sm font-semibold text-blue-600"
                            >
                              Try Again
                            </button>
                          </div>
                        ) : productReviews[product.id]?.length > 0 ? (
                          <div className="mt-4 space-y-4">
                            {productReviews[product.id].map((review) => (
                              <div
                                key={review.id}
                                className="rounded-xl border border-slate-200 bg-white p-4"
                              >
                                <div className="flex items-center justify-between gap-2">
                                  <RatingStars
                                    rating={review.rating}
                                    size={14}
                                  />

                                  <span className="text-xs text-slate-400">
                                    {review.created_at
                                      ? new Date(
                                          review.created_at
                                        ).toLocaleDateString('en-IN')
                                      : ''}
                                  </span>
                                </div>

                                {review.title && (
                                  <h5 className="mt-2 text-sm font-bold text-slate-800">
                                    {review.title}
                                  </h5>
                                )}

                                {review.comment && (
                                  <p className="mt-1 whitespace-pre-wrap text-sm leading-6 text-slate-600">
                                    {review.comment}
                                  </p>
                                )}

                                <p className="mt-2 text-xs text-slate-400">
                                  Verified purchase
                                </p>
                              </div>
                            ))}
                          </div>
                        ) : (
                          <p className="mt-3 text-sm text-slate-500">
                            No approved customer reviews yet.
                          </p>
                        )}
                      </div>
                    )}
                  </article>
                );
              })}
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="mt-8 flex flex-wrap items-center justify-center gap-2">
                <button
                  type="button"
                  disabled={currentPage === 1}
                  onClick={() => setCurrentPage((page) => page - 1)}
                  className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-40"
                >
                  Previous
                </button>

                {Array.from(
                  { length: totalPages },
                  (_, index) => index + 1
                ).map((page) => (
                  <button
                    key={page}
                    type="button"
                    onClick={() => setCurrentPage(page)}
                    className={`h-10 min-w-10 rounded-lg px-3 text-sm font-semibold transition ${
                      currentPage === page
                        ? 'bg-blue-600 text-white'
                        : 'border border-slate-300 text-slate-700 hover:bg-slate-100'
                    }`}
                  >
                    {page}
                  </button>
                ))}

                <button
                  type="button"
                  disabled={currentPage === totalPages}
                  onClick={() => setCurrentPage((page) => page + 1)}
                  className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-40"
                >
                  Next
                </button>
              </div>
            )}
          </>
        )}
      </section>
    </div>
  );
}
