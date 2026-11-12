
import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import api from '../services/api';

function ProductDetails() {
  const { productId } = useParams();

  const [product, setProduct] = useState(null);
  const [inventory, setInventory] = useState(null);
  const [reviews, setReviews] = useState([]);
  const [ratingSummary, setRatingSummary] = useState(null);
  const [orders, setOrders] = useState([]);
  const [myReviews, setMyReviews] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const [selectedOrderId, setSelectedOrderId] = useState('');
  const [selectedRating, setSelectedRating] = useState(5);
  const [reviewTitle, setReviewTitle] = useState('');
  const [reviewComment, setReviewComment] = useState('');
  const [reviewSubmitting, setReviewSubmitting] = useState(false);
  const [reviewMessage, setReviewMessage] = useState('');
  const [reviewError, setReviewError] = useState('');

  const [wishlistIds, setWishlistIds] = useState([]);
  const [cartLoading, setCartLoading] = useState(false);
  const [wishlistLoading, setWishlistLoading] = useState(false);
  const [actionMessage, setActionMessage] = useState('');
  const [actionError, setActionError] = useState('');

  // Submit a customer review
  const submitReview = async (event) => {
    event.preventDefault();

    setReviewSubmitting(true);
    setReviewMessage('');
    setReviewError('');

    try {
      await api.post('/reviews', {
        product_id: Number(productId),
        order_id: Number(selectedOrderId),
        rating: Number(selectedRating),
        title: reviewTitle.trim() || null,
        comment: reviewComment.trim() || null,
      });

      setReviewMessage(
        'Your review was submitted successfully and is awaiting admin approval.'
      );

      setSelectedOrderId('');
      setSelectedRating(5);
      setReviewTitle('');
      setReviewComment('');

      const response = await api.get('/reviews/me');
      setMyReviews(response.data);
    } catch (err) {
      setReviewError(
        err.response?.data?.detail || 'Unable to submit your review.'
      );
    } finally {
      setReviewSubmitting(false);
    }
  };

  // Add product to cart
  const addToCart = async () => {
    try {
      setCartLoading(true);
      setActionMessage('');
      setActionError('');

      await api.post('/cart/items', {
        product_id: Number(productId),
        quantity: 1,
      });

      setActionMessage('Product added to your cart successfully.');
    } catch (err) {
      setActionError(
        err.response?.data?.detail || 'Unable to add product to cart.'
      );
    } finally {
      setCartLoading(false);
    }
  };

  // Add or remove product from wishlist
  const toggleWishlist = async () => {
    try {
      setWishlistLoading(true);
      setActionMessage('');
      setActionError('');

      if (wishlistIds.includes(Number(productId))) {
        await api.delete(`/wishlist/items/${productId}`);

        setWishlistIds((previous) =>
          previous.filter((id) => id !== Number(productId))
        );

        setActionMessage('Product removed from your wishlist.');
      } else {
        await api.post('/wishlist/items', {
          product_id: Number(productId),
        });

        setWishlistIds((previous) => [
          ...previous,
          Number(productId),
        ]);

        setActionMessage('Product added to your wishlist.');
      }
    } catch (err) {
      setActionError(
        err.response?.data?.detail || 'Unable to update wishlist.'
      );
    } finally {
      setWishlistLoading(false);
    }
  };

  // Load product information
  useEffect(() => {
    let active = true;

    const loadProductDetails = async () => {
      setLoading(true);
      setError('');

      try {
        const results = await Promise.allSettled([
          api.get(`/products/${productId}`),
          api.get(`/inventory/${productId}`),
          api.get(`/reviews/products/${productId}/reviews`),
          api.get(`/reviews/products/${productId}/rating-summary`),
          api.get('/orders'),
          api.get('/reviews/me'),
          api.get('/wishlist'),
        ]);

        if (!active) return;

        if (results[0].status === 'rejected') {
          throw new Error('Could not load product details.');
        }

        setProduct(results[0].value.data);

        setInventory(
          results[1].status === 'fulfilled'
            ? results[1].value.data
            : null
        );

        setReviews(
          results[2].status === 'fulfilled'
            ? results[2].value.data
            : []
        );

        setRatingSummary(
          results[3].status === 'fulfilled'
            ? results[3].value.data
            : null
        );

        setOrders(
          results[4].status === 'fulfilled'
            ? results[4].value.data
            : []
        );

        setMyReviews(
          results[5].status === 'fulfilled'
            ? results[5].value.data
            : []
        );

        setWishlistIds(
          results[6].status === 'fulfilled'
            ? results[6].value.data.map((item) => item.product_id)
            : []
        );
      } catch (err) {
        if (active) {
          setError(
            err.response?.data?.detail ||
            err.message ||
            'Something went wrong.'
          );
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    };

    loadProductDetails();

    return () => {
      active = false;
    };
  }, [productId]);

  if (loading) {
    return (
      <div className="p-8 text-center">
        Loading product details...
      </div>
    );
  }

  if (error || !product) {
    return (
      <div className="p-8 text-center text-red-600">
        {error || 'Product not found.'}
      </div>
    );
  }

  const eligibleOrders = orders.filter((order) =>
    order.status === 'Delivered' &&
    order.items?.some(
      (item) =>
        item.product_id === Number(productId) &&
        item.quantity > item.cancelled_quantity
    )
  );

  const alreadyReviewed = myReviews.some(
    (review) => review.product_id === Number(productId)
  );

  const ratingBreakdown = [5, 4, 3, 2, 1].map((star) => {
    const count = reviews.filter(
      (review) => review.rating === star
    ).length;

    const percentage =
      reviews.length > 0
        ? (count / reviews.length) * 100
        : 0;

    return { star, count, percentage };
  });

  return (
    <div className="mx-auto max-w-7xl space-y-8 p-6">

      {/* Product information */}
      <section className="grid gap-8 rounded-2xl bg-white p-6 shadow-sm md:grid-cols-2">
        <div className="flex min-h-80 items-center justify-center rounded-xl bg-gray-50 p-6">
          {product.image_url ? (
            <img
              src={product.image_url}
              alt={product.name}
              className="max-h-96 w-full object-contain"
            />
          ) : (
            <span className="text-gray-400">
              No product image available
            </span>
          )}
        </div>

        <div className="space-y-4">
          <p className="text-sm text-gray-500">
            {product.category}
          </p>

          <h1 className="text-3xl font-bold text-gray-900">
            {product.name}
          </h1>

          {product.brand && (
            <p className="text-gray-600">
              Brand: {product.brand}
            </p>
          )}

          <p className="text-sm text-gray-500">
            SKU: {product.sku}
          </p>

          <p className="text-3xl font-bold text-gray-900">
            ₹{Number(product.price).toLocaleString('en-IN')}
          </p>

          <p className="text-sm text-gray-600">
            {product.description || 'No description available.'}
          </p>

          <div className="font-semibold">
            {inventory && inventory.quantity > 0 ? (
              <span className="text-green-600">
                In Stock ({inventory.quantity} available)
              </span>
            ) : (
              <span className="text-red-600">
                Out of Stock
              </span>
            )}
          </div>

          <div className="flex flex-wrap gap-3 pt-3">
            <button
              type="button"
              onClick={addToCart}
              disabled={
                !inventory ||
                inventory.quantity <= 0 ||
                cartLoading
              }
              className="rounded-xl bg-blue-600 px-6 py-3 font-semibold text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {cartLoading ? 'Adding...' : 'Add to Cart'}
            </button>

            <button
              type="button"
              onClick={toggleWishlist}
              disabled={wishlistLoading}
              className="rounded-xl border border-pink-300 px-6 py-3 font-semibold text-pink-700 transition hover:bg-pink-50 disabled:opacity-50"
            >
              {wishlistLoading
                ? 'Updating...'
                : wishlistIds.includes(Number(productId))
                  ? '♥ Remove from Wishlist'
                  : '♡ Add to Wishlist'}
            </button>
          </div>

          {actionMessage && (
            <p className="text-sm font-medium text-green-700">
              {actionMessage}
            </p>
          )}

          {actionError && (
            <p className="text-sm font-medium text-red-600">
              {actionError}
            </p>
          )}

          <p className="text-sm text-gray-500">
            {ratingSummary?.total_reviews || 0} customer reviews
          </p>
        </div>
      </section>

      {/* Product specifications */}
      <section className="rounded-2xl bg-white p-6 shadow-sm">
        <h2 className="mb-4 text-2xl font-bold">
          Product Specifications
        </h2>

        {product.specifications &&
        Object.keys(product.specifications).length > 0 ? (
          <div className="space-y-3">
            {Object.entries(product.specifications).map(([key, value]) => (
              <div
                key={key}
                className="flex justify-between gap-4 border-b py-2"
              >
                <span className="font-medium text-gray-600">
                  {key}
                </span>

                <span className="text-right text-gray-900">
                  {String(value)}
                </span>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-gray-500">
            No specifications available.
          </p>
        )}
      </section>

      {/* Customer ratings and reviews */}
      <section className="rounded-2xl bg-white p-6 shadow-sm">
        <h2 className="mb-4 text-2xl font-bold">
          Customer Reviews
        </h2>

        <div className="mb-6 grid gap-6 md:grid-cols-2">
          <div>
            <p className="text-5xl font-bold text-gray-900">
              {Number(ratingSummary?.average_rating || 0).toFixed(1)}
              <span className="text-xl text-gray-500"> / 5</span>
            </p>

            <p className="mt-2 text-yellow-500">
              {'★'.repeat(Math.round(ratingSummary?.average_rating || 0))}
              <span className="text-gray-300">
                {'★'.repeat(
                  5 - Math.round(ratingSummary?.average_rating || 0)
                )}
              </span>
            </p>

            <p className="mt-2 text-sm text-gray-500">
              Based on {ratingSummary?.total_reviews || 0} approved reviews
            </p>
          </div>

          <div className="space-y-2">
            {ratingBreakdown.map(({ star, count, percentage }) => (
              <div key={star} className="flex items-center gap-3 text-sm">
                <span className="w-12 shrink-0">
                  {star} star
                </span>

                <div className="h-3 flex-1 overflow-hidden rounded-full bg-gray-200">
                  <div
                    className="h-full rounded-full bg-yellow-400"
                    style={{ width: `${percentage}%` }}
                  />
                </div>

                <span className="w-8 text-right text-gray-500">
                  {count}
                </span>
              </div>
            ))}
          </div>
        </div>

        <p className="text-gray-600">
          Average rating: {ratingSummary?.average_rating ?? 0} / 5
        </p>

        <p className="mb-5 text-gray-600">
          {ratingSummary?.total_reviews ?? 0} approved reviews
        </p>

        {reviews.length === 0 ? (
          <p className="text-gray-500">
            No approved reviews yet.
          </p>
        ) : (
          <div className="space-y-5">
            {reviews.map((review) => (
              <article key={review.id} className="border-b pb-5">
                <p className="text-lg font-semibold">
                  {'★'.repeat(review.rating)}
                  <span className="text-gray-300">
                    {'★'.repeat(5 - review.rating)}
                  </span>
                </p>

                <h3 className="mt-2 font-semibold">
                  {review.title || 'Customer review'}
                </h3>

                <p className="mt-1 text-gray-600">
                  {review.comment || 'No comment provided.'}
                </p>

                <p className="mt-2 text-xs text-gray-400">
                  {new Date(review.created_at).toLocaleDateString('en-IN')}
                  {' · Verified purchase'}
                </p>
              </article>
            ))}
          </div>
        )}
      </section>

      {/* Write a review */}
      <section className="rounded-2xl bg-white p-6 shadow-sm">
        <h2 className="text-2xl font-bold">
          Write a Review
        </h2>

        {alreadyReviewed ? (
          <p className="mt-3 text-gray-600">
            You have already submitted a review for this product.
          </p>
        ) : eligibleOrders.length > 0 ? (
          <form
            onSubmit={submitReview}
            className="mt-5 max-w-2xl space-y-5"
          >
            <div>
              <label className="mb-2 block text-sm font-semibold">
                Select Delivered Order
              </label>

              <select
                value={selectedOrderId}
                onChange={(event) => setSelectedOrderId(event.target.value)}
                required
                className="w-full rounded-xl border border-gray-300 p-3"
              >
                <option value="">Choose an order</option>

                {eligibleOrders.map((order) => (
                  <option key={order.id} value={order.id}>
                    {order.order_number} — ₹{order.total_amount}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="mb-2 block text-sm font-semibold">
                Your Rating
              </label>

              <div className="flex gap-2">
                {[1, 2, 3, 4, 5].map((star) => (
                  <button
                    key={star}
                    type="button"
                    onClick={() => setSelectedRating(star)}
                    className={`text-3xl ${
                      star <= selectedRating
                        ? 'text-yellow-400'
                        : 'text-gray-300'
                    }`}
                    aria-label={`${star} star rating`}
                  >
                    ★
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label className="mb-2 block text-sm font-semibold">
                Review Title (Optional)
              </label>

              <input
                type="text"
                value={reviewTitle}
                onChange={(event) => setReviewTitle(event.target.value)}
                minLength={3}
                maxLength={120}
                placeholder="Summarize your experience"
                className="w-full rounded-xl border border-gray-300 p-3"
              />
            </div>

            <div>
              <label className="mb-2 block text-sm font-semibold">
                Your Review (Optional)
              </label>

              <textarea
                value={reviewComment}
                onChange={(event) => setReviewComment(event.target.value)}
                minLength={5}
                maxLength={2000}
                rows={5}
                placeholder="Tell other customers about this product..."
                className="w-full rounded-xl border border-gray-300 p-3"
              />
            </div>

            {reviewError && (
              <p className="text-sm text-red-600">
                {reviewError}
              </p>
            )}

            {reviewMessage && (
              <p className="text-sm text-green-700">
                {reviewMessage}
              </p>
            )}

            <button
              type="submit"
              disabled={!selectedOrderId || reviewSubmitting}
              className="rounded-xl bg-blue-600 px-6 py-3 font-semibold text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {reviewSubmitting ? 'Submitting...' : 'Submit Review'}
            </button>
          </form>
        ) : (
          <p className="mt-3 text-gray-500">
            You can review this product after purchasing it and receiving a
            delivered order.
          </p>
        )}
      </section>
    </div>
  );
}

export default ProductDetails;
