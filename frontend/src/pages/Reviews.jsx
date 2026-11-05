import { useEffect, useMemo, useState } from 'react';
import {
  RefreshCw,
  Star,
  CheckCircle2,
  XCircle,
  Clock3,
  AlertCircle,
  MessageSquare,
} from 'lucide-react';

import api from '../services/api';

export default function Reviews() {
  const [reviews, setReviews] = useState([]);
  const [filter, setFilter] = useState('PENDING');
  const [loading, setLoading] = useState(true);
  const [processingId, setProcessingId] = useState(null);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');

  async function loadReviews() {
    setLoading(true);
    setError('');

    try {
      const response = await api.get('/reviews/admin');

      setReviews(
        Array.isArray(response.data) ? response.data : []
      );
    } catch (err) {
      console.error('Review loading error:', err);

      setError(
        err.response?.data?.detail ||
          'Unable to load reviews.'
      );
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadReviews();
  }, []);

  async function handleModeration(reviewId, status) {
    setProcessingId(reviewId);
    setError('');
    setMessage('');

    try {
      const response = await api.patch(
        `/reviews/admin/${reviewId}/moderation`,
        { status }
      );

      setReviews((previousReviews) =>
        previousReviews.map((review) =>
          review.id === reviewId ? response.data : review
        )
      );

      setMessage(
        `Review #${reviewId} was ${status.toLowerCase()}.`
      );
    } catch (err) {
      console.error('Review moderation error:', err);

      setError(
        err.response?.data?.detail ||
          'Unable to update review status.'
      );
    } finally {
      setProcessingId(null);
    }
  }

  const filteredReviews = useMemo(() => {
    if (filter === 'ALL') {
      return reviews;
    }

    return reviews.filter(
      (review) => review.status === filter
    );
  }, [reviews, filter]);

  const pendingCount = reviews.filter(
    (review) => review.status === 'PENDING'
  ).length;

  const approvedCount = reviews.filter(
    (review) => review.status === 'APPROVED'
  ).length;

  const rejectedCount = reviews.filter(
    (review) => review.status === 'REJECTED'
  ).length;

  function formatDate(dateValue) {
    if (!dateValue) return 'Not available';

    return new Date(dateValue).toLocaleDateString('en-IN', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
    });
  }

  function getStatusStyle(status) {
    if (status === 'APPROVED') {
      return 'bg-green-100 text-green-700';
    }

    if (status === 'REJECTED') {
      return 'bg-red-100 text-red-700';
    }

    return 'bg-yellow-100 text-yellow-700';
  }

  return (
    <div className="space-y-6">
      {/* Page heading */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">
            Customer Reviews
          </h1>

          <p className="mt-1 text-sm text-slate-500">
            Manage and moderate customer product reviews.
          </p>
        </div>

        <button
          onClick={loadReviews}
          disabled={loading}
          className="flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-50"
        >
          <RefreshCw
            size={17}
            className={loading ? 'animate-spin' : ''}
          />
          Refresh
        </button>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-2xl border border-slate-200 bg-white p-5">
          <p className="text-sm text-slate-500">Total Reviews</p>
          <h2 className="mt-2 text-3xl font-bold text-slate-900">
            {reviews.length}
          </h2>
        </div>

        <div className="rounded-2xl border border-yellow-200 bg-yellow-50 p-5">
          <p className="text-sm text-yellow-700">Pending</p>
          <h2 className="mt-2 text-3xl font-bold text-yellow-800">
            {pendingCount}
          </h2>
        </div>

        <div className="rounded-2xl border border-green-200 bg-green-50 p-5">
          <p className="text-sm text-green-700">Approved</p>
          <h2 className="mt-2 text-3xl font-bold text-green-800">
            {approvedCount}
          </h2>
        </div>

        <div className="rounded-2xl border border-red-200 bg-red-50 p-5">
          <p className="text-sm text-red-700">Rejected</p>
          <h2 className="mt-2 text-3xl font-bold text-red-800">
            {rejectedCount}
          </h2>
        </div>
      </div>

      {/* Messages */}
      {error && (
        <div className="flex items-center gap-2 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          <AlertCircle size={18} />
          {error}
        </div>
      )}

      {message && (
        <div className="flex items-center gap-2 rounded-xl border border-green-200 bg-green-50 p-4 text-sm text-green-700">
          <CheckCircle2 size={18} />
          {message}
        </div>
      )}

      {/* Filter buttons */}
      <div className="flex flex-wrap gap-2">
        {[
          { label: 'All Reviews', value: 'ALL' },
          { label: 'Pending', value: 'PENDING' },
          { label: 'Approved', value: 'APPROVED' },
          { label: 'Rejected', value: 'REJECTED' },
        ].map((option) => (
          <button
            key={option.value}
            onClick={() => setFilter(option.value)}
            className={`rounded-xl px-4 py-2.5 text-sm font-semibold transition ${
              filter === option.value
                ? 'bg-blue-600 text-white'
                : 'border border-slate-200 bg-white text-slate-600 hover:bg-slate-50'
            }`}
          >
            {option.label}
          </button>
        ))}
      </div>

      {/* Reviews list */}
      {loading ? (
        <div className="rounded-2xl border border-slate-200 bg-white p-10 text-center">
          <RefreshCw
            size={28}
            className="mx-auto animate-spin text-blue-600"
          />
          <p className="mt-3 text-sm text-slate-500">
            Loading reviews...
          </p>
        </div>
      ) : filteredReviews.length === 0 ? (
        <div className="rounded-2xl border border-slate-200 bg-white p-10 text-center">
          <MessageSquare
            size={36}
            className="mx-auto text-slate-300"
          />

          <h3 className="mt-3 font-semibold text-slate-800">
            No reviews found
          </h3>

          <p className="mt-1 text-sm text-slate-500">
            There are no reviews in this category.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {filteredReviews.map((review) => (
            <div
              key={review.id}
              className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"
            >
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <h3 className="font-bold text-slate-900">
                      {review.title || 'Customer Review'}
                    </h3>

                    <span
                      className={`rounded-full px-3 py-1 text-xs font-bold ${getStatusStyle(
                        review.status
                      )}`}
                    >
                      {review.status}
                    </span>
                  </div>

                  <div className="mt-2 flex items-center gap-1">
                    {Array.from(
                      { length: review.rating },
                      (_, index) => (
                        <Star
                          key={index}
                          size={17}
                          className="fill-yellow-400 text-yellow-400"
                        />
                      )
                    )}

                    <span className="ml-2 text-sm font-semibold text-slate-700">
                      {review.rating}/5
                    </span>
                  </div>
                </div>

                <p className="text-xs text-slate-500">
                  Review #{review.id}
                </p>
              </div>

              <p className="mt-4 whitespace-pre-wrap text-sm leading-6 text-slate-600">
                {review.comment || 'No written comment provided.'}
              </p>

              {/* Review information */}
              <div className="mt-5 grid grid-cols-2 gap-3 rounded-xl bg-slate-50 p-4 text-sm sm:grid-cols-4">
                <div>
                  <p className="text-xs text-slate-400">Customer ID</p>
                  <p className="mt-1 font-semibold text-slate-700">
                    {review.user_id}
                  </p>
                </div>

                <div>
                  <p className="text-xs text-slate-400">Product ID</p>
                  <p className="mt-1 font-semibold text-slate-700">
                    {review.product_id}
                  </p>
                </div>

                <div>
                  <p className="text-xs text-slate-400">Order ID</p>
                  <p className="mt-1 font-semibold text-slate-700">
                    {review.order_id}
                  </p>
                </div>

                <div>
                  <p className="text-xs text-slate-400">Submitted</p>
                  <p className="mt-1 font-semibold text-slate-700">
                    {formatDate(review.created_at)}
                  </p>
                </div>
              </div>

              {/* Moderation actions */}
              {review.status === 'PENDING' && (
                <div className="mt-5 flex flex-wrap justify-end gap-3">
                  <button
                    onClick={() =>
                      handleModeration(review.id, 'REJECTED')
                    }
                    disabled={processingId === review.id}
                    className="flex items-center gap-2 rounded-xl border border-red-200 px-4 py-2.5 text-sm font-semibold text-red-600 hover:bg-red-50 disabled:opacity-50"
                  >
                    <XCircle size={17} />
                    Reject
                  </button>

                  <button
                    onClick={() =>
                      handleModeration(review.id, 'APPROVED')
                    }
                    disabled={processingId === review.id}
                    className="flex items-center gap-2 rounded-xl bg-green-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-green-700 disabled:opacity-50"
                  >
                    <CheckCircle2 size={17} />
                    {processingId === review.id
                      ? 'Processing...'
                      : 'Approve'}
                  </button>
                </div>
              )}

              {review.status !== 'PENDING' && (
                <div className="mt-4 flex items-center gap-2 text-xs text-slate-500">
                  <Clock3 size={14} />
                  This review has already been moderated.
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}