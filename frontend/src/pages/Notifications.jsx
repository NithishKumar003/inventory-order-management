
import { useEffect, useState } from 'react';
import {
  Bell,
  Check,
  CheckCheck,
  Clock,
  Inbox,
  RefreshCw,
} from 'lucide-react';

import api from '../services/api';

function Notifications() {
  const [notifications, setNotifications] = useState([]);
  const [activeFilter, setActiveFilter] = useState('all');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [updatingId, setUpdatingId] = useState(null);

  // Fetch notifications belonging to the logged-in user.
  const fetchNotifications = async () => {
    try {
      setError('');

      const response = await api.get('/notifications/');

      setNotifications(response.data);
    } catch (error) {
      console.error('Failed to fetch notifications:', error);

      setError(
        error.response?.data?.detail ||
        'Unable to load notifications. Please try again.'
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchNotifications();
  }, []);

  // Mark one notification as read.
  const markAsRead = async (notificationId) => {
    try {
      setUpdatingId(notificationId);

      const response = await api.patch(
        `/notifications/${notificationId}/read`,
        { is_read: true }
      );

      setNotifications((previousNotifications) =>
        previousNotifications.map((notification) =>
          notification.id === notificationId
            ? response.data
            : notification
        )
      );
    } catch (error) {
      console.error('Failed to update notification:', error);

      setError(
        error.response?.data?.detail ||
        'Unable to update notification. Please try again.'
      );
    } finally {
      setUpdatingId(null);
    }
  };

  const unreadCount = notifications.filter(
    (notification) => !notification.is_read
  ).length;

  const filteredNotifications = notifications.filter(
    (notification) =>
      activeFilter === 'all' ||
      !notification.is_read
  );

  const formatDate = (dateValue) => {
    return new Date(dateValue).toLocaleString('en-IN', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  return (
    <div className="space-y-6">

      {/* Page heading */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">
            Notifications
          </h1>

          <p className="mt-1 text-sm text-slate-500">
            Stay updated with your orders and account activity.
          </p>
        </div>

        <button
          type="button"
          onClick={() => {
            setLoading(true);
            fetchNotifications();
          }}
          disabled={loading}
          className="inline-flex items-center justify-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-semibold text-slate-700 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60"
        >
          <RefreshCw
            size={16}
            className={loading ? 'animate-spin' : ''}
          />
          Refresh
        </button>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">

        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <div className="flex items-center gap-3">
            <div className="rounded-xl bg-blue-50 p-3 text-blue-600">
              <Bell size={22} />
            </div>

            <div>
              <p className="text-sm text-slate-500">
                Total Notifications
              </p>

              <p className="text-2xl font-bold text-slate-900">
                {notifications.length}
              </p>
            </div>
          </div>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <div className="flex items-center gap-3">
            <div className="rounded-xl bg-amber-50 p-3 text-amber-600">
              <Clock size={22} />
            </div>

            <div>
              <p className="text-sm text-slate-500">
                Unread Notifications
              </p>

              <p className="text-2xl font-bold text-slate-900">
                {unreadCount}
              </p>
            </div>
          </div>
        </div>

      </div>

      {/* Filters */}
      <div className="flex items-center gap-3 border-b border-slate-200">
        <button
          type="button"
          onClick={() => setActiveFilter('all')}
          className={`border-b-2 px-4 py-3 text-sm font-semibold transition ${
            activeFilter === 'all'
              ? 'border-blue-600 text-blue-600'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          All ({notifications.length})
        </button>

        <button
          type="button"
          onClick={() => setActiveFilter('unread')}
          className={`border-b-2 px-4 py-3 text-sm font-semibold transition ${
            activeFilter === 'unread'
              ? 'border-blue-600 text-blue-600'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          Unread ({unreadCount})
        </button>
      </div>

      {/* Error message */}
      {error && (
        <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {/* Loading */}
      {loading ? (
        <div className="flex flex-col items-center justify-center rounded-2xl border border-slate-200 bg-white py-16">
          <RefreshCw
            size={28}
            className="animate-spin text-blue-600"
          />

          <p className="mt-3 text-sm text-slate-500">
            Loading notifications...
          </p>
        </div>
      ) : filteredNotifications.length === 0 ? (

        /* Empty state */
        <div className="flex flex-col items-center justify-center rounded-2xl border border-slate-200 bg-white px-6 py-16 text-center">
          <div className="rounded-full bg-slate-100 p-5 text-slate-400">
            <Inbox size={32} />
          </div>

          <h2 className="mt-4 text-lg font-semibold text-slate-800">
            {activeFilter === 'unread'
              ? 'No unread notifications'
              : 'No notifications yet'}
          </h2>

          <p className="mt-2 max-w-sm text-sm text-slate-500">
            {activeFilter === 'unread'
              ? 'You have read all your notifications.'
              : 'Notifications about your orders and account activity will appear here.'}
          </p>
        </div>

      ) : (

        /* Notification list */
        <div className="space-y-3">

          {filteredNotifications.map((notification) => (
            <div
              key={notification.id}
              className={`rounded-2xl border p-5 transition ${
                notification.is_read
                  ? 'border-slate-200 bg-white'
                  : 'border-blue-200 bg-blue-50/40'
              }`}
            >
              <div className="flex items-start gap-4">

                <div
                  className={`mt-1 rounded-xl p-3 ${
                    notification.is_read
                      ? 'bg-slate-100 text-slate-500'
                      : 'bg-blue-100 text-blue-600'
                  }`}
                >
                  <Bell size={20} />
                </div>

                <div className="min-w-0 flex-1">

                  <div className="flex flex-wrap items-center gap-2">
                    <h3 className="font-semibold text-slate-900">
                      {notification.title}
                    </h3>

                    {!notification.is_read && (
                      <span className="rounded-full bg-blue-100 px-2.5 py-1 text-xs font-semibold text-blue-700">
                        New
                      </span>
                    )}
                  </div>

                  <p className="mt-2 text-sm leading-6 text-slate-600">
                    {notification.message}
                  </p>

                  <div className="mt-3 flex flex-wrap items-center gap-3 text-xs text-slate-400">
                    <span>
                      {formatDate(notification.created_at)}
                    </span>

                    <span className="rounded-md bg-slate-100 px-2 py-1 text-slate-500">
                      {notification.notification_type.replaceAll('_', ' ')}
                    </span>
                  </div>

                </div>

                {!notification.is_read && (
                  <button
                    type="button"
                    onClick={() => markAsRead(notification.id)}
                    disabled={updatingId === notification.id}
                    title="Mark as read"
                    className="inline-flex shrink-0 items-center gap-2 rounded-lg border border-blue-200 bg-white px-3 py-2 text-xs font-semibold text-blue-700 transition hover:bg-blue-50 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    {updatingId === notification.id ? (
                      <RefreshCw
                        size={15}
                        className="animate-spin"
                      />
                    ) : (
                      <Check size={15} />
                    )}

                    <span className="hidden sm:inline">
                      Mark read
                    </span>
                  </button>
                )}

                {notification.is_read && (
                  <div
                    className="shrink-0 text-emerald-600"
                    title="Already read"
                  >
                    <CheckCheck size={20} />
                  </div>
                )}

              </div>
            </div>
          ))}

        </div>
      )}

    </div>
  );
}

export default Notifications;
