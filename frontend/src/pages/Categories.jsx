
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  LayoutGrid,
  ArrowRight,
  Loader2,
  Package,
  AlertCircle,
} from 'lucide-react';

import api from '../services/api';

export default function Categories() {
  const navigate = useNavigate();

  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    async function fetchCategories() {
      try {
        setLoading(true);
        setError('');

        const response = await api.get('/products/categories');

        setCategories(
          Array.isArray(response.data) ? response.data : []
        );
      } catch (err) {
        console.error('Unable to load categories:', err);

        setError(
          err.response?.data?.detail ||
          'Unable to load categories.'
        );
      } finally {
        setLoading(false);
      }
    }

    fetchCategories();
  }, []);

  function openCategory(category) {
    navigate(`/shop?category=${encodeURIComponent(category)}`);
  }

  return (
    <div className="space-y-8">
      <section className="rounded-3xl bg-gradient-to-r from-blue-700 via-blue-600 to-indigo-600 p-8 text-white shadow-lg sm:p-10">
        <div className="flex items-center gap-3">
          <LayoutGrid size={30} />
          <span className="text-sm font-semibold uppercase tracking-wider text-blue-100">
            Explore StockFlow
          </span>
        </div>

        <h1 className="mt-5 text-3xl font-extrabold sm:text-4xl">
          Shop by Category
        </h1>

        <p className="mt-3 max-w-xl text-sm leading-6 text-blue-100 sm:text-base">
          Explore our product collections and find exactly what
          you are looking for.
        </p>
      </section>

      <section>
        <div className="mb-6">
          <h2 className="text-2xl font-bold text-slate-900">
            All Categories
          </h2>
          <p className="mt-1 text-sm text-slate-500">
            Browse products by category.
          </p>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-16">
            <Loader2 className="animate-spin text-blue-600" size={32} />
          </div>
        ) : error ? (
          <div className="rounded-2xl border border-red-200 bg-red-50 p-6 text-center">
            <AlertCircle className="mx-auto mb-2 text-red-500" size={28} />
            <p className="text-sm text-red-700">{error}</p>
          </div>
        ) : categories.length === 0 ? (
          <div className="rounded-2xl border border-slate-200 bg-white p-12 text-center">
            <Package className="mx-auto mb-3 text-slate-400" size={36} />
            <p className="font-semibold text-slate-700">
              No categories available.
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {categories.map((category, index) => (
              <button
                key={category}
                type="button"
                onClick={() => openCategory(category)}
                className="group flex min-h-36 items-center justify-between rounded-2xl border border-slate-200 bg-white p-6 text-left shadow-sm transition hover:-translate-y-1 hover:border-blue-300 hover:shadow-lg"
              >
                <div>
                  <div className="mb-4 flex h-11 w-11 items-center justify-center rounded-xl bg-blue-50 text-blue-600 transition group-hover:bg-blue-600 group-hover:text-white">
                    <LayoutGrid size={21} />
                  </div>

                  <h3 className="text-lg font-bold text-slate-800">
                    {category}
                  </h3>

                  <p className="mt-1 text-xs text-slate-500">
                    Explore collection
                  </p>
                </div>

                <ArrowRight
                  size={20}
                  className="text-slate-400 transition group-hover:translate-x-1 group-hover:text-blue-600"
                />
              </button>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
