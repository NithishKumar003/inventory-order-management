
import { useEffect, useState } from 'react';
import { AlertTriangle, Loader2, Save, Settings, RefreshCw } from 'lucide-react';

import api from '../services/api';

export default function AdminSettings() {
  const [threshold, setThreshold] = useState('10');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');

  async function loadSettings() {
    try {
      setLoading(true);
      setError('');

      const response = await api.get('/inventory/settings');

      setThreshold(String(response.data.low_stock_threshold));
    } catch (err) {
      setError(
        err.response?.data?.detail ||
        'Unable to load inventory settings.'
      );
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadSettings();
  }, []);

  async function handleSave(event) {
    event.preventDefault();

    const value = Number(threshold);

    if (!Number.isInteger(value) || value < 0 || value > 100000) {
      setError('Enter a whole number between 0 and 100000.');
      setMessage('');
      return;
    }

    try {
      setSaving(true);
      setError('');
      setMessage('');

      const response = await api.put('/inventory/settings', {
        low_stock_threshold: value,
      });

      setThreshold(String(response.data.low_stock_threshold));
      setMessage('Settings saved successfully.');
    } catch (err) {
      setError(
        err.response?.data?.detail ||
        'Unable to save settings.'
      );
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Settings</h1>
        <p className="mt-1 text-sm text-gray-500">
          Manage your inventory system preferences.
        </p>
      </div>

      <div className="max-w-2xl rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
        <div className="mb-6 flex items-center gap-3">
          <div className="rounded-xl bg-blue-50 p-3 text-blue-600">
            <Settings size={23} />
          </div>
          <div>
            <h2 className="font-semibold text-gray-900">
              Inventory Settings
            </h2>
            <p className="text-sm text-gray-500">
              Configure stock alert preferences.
            </p>
          </div>
        </div>

        {loading ? (
          <div className="flex items-center gap-2 py-6 text-sm text-gray-500">
            <Loader2 size={18} className="animate-spin" />
            Loading settings...
          </div>
        ) : (
          <form onSubmit={handleSave} className="space-y-5">
            <div>
              <label
                htmlFor="low-stock-threshold"
                className="mb-2 block text-sm font-medium text-gray-700"
              >
                Low Stock Threshold
              </label>

              <input
                id="low-stock-threshold"
                type="number"
                min="0"
                max="100000"
                step="1"
                value={threshold}
                onChange={(event) => {
                  setThreshold(event.target.value);
                  setError('');
                  setMessage('');
                }}
                className="w-full rounded-lg border border-gray-300 px-4 py-3 text-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
                required
              />

              <p className="mt-2 text-xs text-gray-500">
                Products with stock at or below this quantity will appear
                in low-stock alerts. Default value: 10.
              </p>
            </div>

            <div className="flex items-start gap-2 rounded-lg bg-amber-50 p-3 text-sm text-amber-800">
              <AlertTriangle size={18} className="mt-0.5 shrink-0" />
              <p>
                Changing this value affects the inventory low-stock
                endpoint and reports that use its default threshold.
              </p>
            </div>

            {error && (
              <p className="rounded-lg bg-red-50 p-3 text-sm text-red-700">
                {error}
              </p>
            )}

            {message && (
              <p className="rounded-lg bg-green-50 p-3 text-sm text-green-700">
                {message}
              </p>
            )}

            <div className="flex flex-wrap gap-3">
              <button
                type="submit"
                disabled={saving}
                className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {saving ? (
                  <Loader2 size={17} className="animate-spin" />
                ) : (
                  <Save size={17} />
                )}
                {saving ? 'Saving...' : 'Save Settings'}
              </button>

              <button
                type="button"
                onClick={loadSettings}
                disabled={saving || loading}
                className="inline-flex items-center gap-2 rounded-lg border border-gray-300 px-5 py-2.5 text-sm font-semibold text-gray-700 transition hover:bg-gray-50 disabled:opacity-60"
              >
                <RefreshCw size={17} />
                Reload
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
