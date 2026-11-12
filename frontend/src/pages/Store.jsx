
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ArrowRight,
  ShoppingBag,
  Package,
  Star,
  Sparkles,
  LayoutGrid,
  RefreshCw,
} from 'lucide-react';
import api from '../services/api';

function formatPrice(price) {
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 0,
  }).format(price || 0);
}

function ProductCard({ product, rating, onClick }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="group overflow-hidden rounded-2xl border border-slate-200 bg-white text-left shadow-sm transition hover:-translate-y-1 hover:shadow-lg"
    >
      <div className="relative flex h-48 items-center justify-center overflow-hidden bg-slate-100 p-4">
        <Package size={42} className="absolute text-slate-300" />

        {product.image_url && (
          <img
            src={product.image_url}
            alt={product.name}
            loading="lazy"
            onError={(event) => {
              event.currentTarget.style.display = 'none';
            }}
            className="relative z-10 h-full w-full object-contain transition duration-300 group-hover:scale-105"
          />
        )}
      </div>

      <div className="p-4">
        <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-blue-600">
          {product.category || 'General'}
        </p>

        <h3 className="truncate font-bold text-slate-800">
          {product.name}
        </h3>

        <p className="mt-2 text-lg font-extrabold text-slate-900">
          {formatPrice(product.price)}
        </p>

        {rating && rating.total_reviews > 0 && (
          <div className="mt-2 flex items-center gap-1 text-sm">
            <Star size={15} className="fill-yellow-400 text-yellow-400" />
            <span className="font-semibold text-slate-700">
              {Number(rating.average_rating).toFixed(1)}
            </span>
            <span className="text-slate-400">
              ({rating.total_reviews} reviews)
            </span>
          </div>
        )}

        <div className="mt-4 flex items-center justify-between border-t border-slate-100 pt-3 text-sm font-semibold text-blue-600">
          View Details
          <ArrowRight size={16} className="transition group-hover:translate-x-1" />
        </div>
      </div>
    </button>
  );
}

function SectionHeading({ eyebrow, title, description, onViewAll }) {
  return (
    <div className="mb-6 flex flex-col justify-between gap-3 sm:flex-row sm:items-end">
      <div>
        <p className="mb-1 text-xs font-bold uppercase tracking-widest text-blue-600">
          {eyebrow}
        </p>
        <h2 className="text-2xl font-extrabold text-slate-900 sm:text-3xl">
          {title}
        </h2>
        <p className="mt-2 text-sm text-slate-500">{description}</p>
      </div>

      {onViewAll && (
        <button
          type="button"
          onClick={onViewAll}
          className="flex items-center gap-2 text-sm font-bold text-blue-600 hover:text-blue-800"
        >
          View All <ArrowRight size={16} />
        </button>
      )}
    </div>
  );
}

export default function Store() {
  const navigate = useNavigate();

  const [products, setProducts] = useState([]);
  const [categories, setCategories] = useState([]);
  const [ratings, setRatings] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;

    async function loadHomepage() {
      try {
        setLoading(true);
        setError('');

        const [productResponse, categoryResponse] = await Promise.all([
          api.get('/products/paginated', {
            params: { skip: 0, limit: 100 },
          }),
          api.get('/products/categories'),
        ]);

        if (cancelled) return;

        const productList = productResponse.data.items || [];
        setProducts(productList);

        setCategories(categoryResponse.data.value || []);

        const ratingResults = await Promise.all(
          productList.map(async (product) => {
            try {
              const response = await api.get(
                `/reviews/products/${product.id}/rating-summary`
              );

              return [product.id, response.data];
            } catch {
              return [product.id, null];
            }
          })
        );

        if (!cancelled) {
          setRatings(Object.fromEntries(ratingResults));
        }
      } catch (err) {
        if (!cancelled) {
          setError(
            err.response?.data?.detail ||
              'Unable to load the homepage. Please try again.'
          );
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    loadHomepage();

    return () => {
      cancelled = true;
    };
  }, []);

  const newArrivals = [...products]
    .sort(
      (a, b) =>
        new Date(b.created_at).getTime() -
        new Date(a.created_at).getTime()
    )
    .slice(0, 4);

  const topRated = products
    .filter((product) => {
      const rating = ratings[product.id];
      return rating && Number(rating.total_reviews) > 0;
    })
    .sort((a, b) => {
      const ratingA = ratings[a.id];
      const ratingB = ratings[b.id];

      return (
        Number(ratingB.average_rating) -
          Number(ratingA.average_rating) ||
        Number(ratingB.total_reviews) -
          Number(ratingA.total_reviews)
      );
    })
    .slice(0, 4);

  return (
    <div className="space-y-12 pb-8">
      {/* Hero Banner */}
      <section className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-blue-700 via-blue-600 to-indigo-700 px-6 py-14 text-white shadow-xl sm:px-12 sm:py-20">
        <div className="absolute -right-20 -top-20 h-72 w-72 rounded-full bg-white/10" />
        <div className="absolute -bottom-28 right-40 h-64 w-64 rounded-full bg-white/10" />

        <div className="relative z-10 max-w-2xl">
          <span className="inline-flex items-center gap-2 rounded-full border border-white/30 bg-white/10 px-4 py-2 text-xs font-bold uppercase tracking-wider">
            <Sparkles size={15} />
            Welcome to StockFlow
          </span>

          <h1 className="mt-6 text-4xl font-extrabold leading-tight sm:text-5xl lg:text-6xl">
            Discover products you'll love.
          </h1>

          <p className="mt-5 max-w-xl text-sm leading-7 text-blue-100 sm:text-base">
            Explore our collection, discover new arrivals and find the
            products that make everyday life better.
          </p>

          <div className="mt-8 flex flex-wrap gap-3">
            <button
              onClick={() => navigate('/shop')}
              className="flex items-center gap-2 rounded-xl bg-white px-6 py-3 font-bold text-blue-700 shadow-lg transition hover:bg-blue-50"
            >
              <ShoppingBag size={18} />
              Shop Now
              <ArrowRight size={17} />
            </button>

            <button
              onClick={() => navigate('/categories')}
              className="rounded-xl border border-white/40 px-6 py-3 font-bold text-white transition hover:bg-white/10"
            >
              Explore Categories
            </button>
          </div>
        </div>
      </section>

      {/* Loading and Error */}
      {loading && (
        <div className="flex items-center justify-center gap-3 py-12 text-slate-500">
          <RefreshCw size={20} className="animate-spin" />
          Loading your shopping experience...
        </div>
      )}

      {error && (
        <div className="rounded-2xl border border-red-200 bg-red-50 p-5 text-red-700">
          {error}
          <button
            onClick={() => window.location.reload()}
            className="ml-3 font-bold underline"
          >
            Retry
          </button>
        </div>
      )}

      {!loading && !error && (
        <>
          {/* Categories */}
          <section>
            <SectionHeading
              eyebrow="Browse Collections"
              title="Shop by Category"
              description="Find exactly what you're looking for."
              onViewAll={() => navigate('/categories')}
            />

            <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
              {categories.map((category, index) => (
                <button
                  key={category}
                  onClick={() =>
                    navigate(
                      `/shop?category=${encodeURIComponent(category)}`
                    )
                  }
                  className="group flex items-center justify-between rounded-2xl border border-slate-200 bg-white p-5 text-left shadow-sm transition hover:border-blue-300 hover:bg-blue-50"
                >
                  <div>
                    <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-xl bg-blue-100 text-blue-700">
                      <LayoutGrid size={20} />
                    </div>
                    <h3 className="font-bold text-slate-800">
                      {category}
                    </h3>
                    <p className="mt-1 text-xs text-slate-500">
                      Explore collection
                    </p>
                  </div>
                  <ArrowRight
                    size={18}
                    className="text-slate-400 transition group-hover:translate-x-1 group-hover:text-blue-600"
                  />
                </button>
              ))}
            </div>
          </section>

          {/* New Arrivals */}
          <section>
            <SectionHeading
              eyebrow="Fresh Finds"
              title="New Arrivals"
              description="Check out the latest products added to our store."
              onViewAll={() => navigate('/shop')}
            />

            {newArrivals.length > 0 ? (
              <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
                {newArrivals.map((product) => (
                  <ProductCard
                    key={product.id}
                    product={product}
                    rating={ratings[product.id]}
                    onClick={() => navigate(`/products/${product.id}`)}
                  />
                ))}
              </div>
            ) : (
              <p className="rounded-xl bg-white p-6 text-center text-slate-500">
                No products available yet.
              </p>
            )}
          </section>

          {/* Top Rated */}
          <section>
            <SectionHeading
              eyebrow="Customer Favourites"
              title="Top Rated Products"
              description="Products ranked using actual customer reviews."
              onViewAll={() => navigate('/shop')}
            />

            {topRated.length > 0 ? (
              <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
                {topRated.map((product) => (
                  <ProductCard
                    key={product.id}
                    product={product}
                    rating={ratings[product.id]}
                    onClick={() => navigate(`/products/${product.id}`)}
                  />
                ))}
              </div>
            ) : (
              <div className="rounded-2xl border border-slate-200 bg-white p-8 text-center">
                <Star size={30} className="mx-auto mb-3 text-yellow-400" />
                <h3 className="font-bold text-slate-800">
                  Reviews are coming soon
                </h3>
                <p className="mt-2 text-sm text-slate-500">
                  Customer-rated products will appear here once reviews are available.
                </p>
              </div>
            )}
          </section>

          {/* Bottom CTA */}
          <section className="flex flex-col items-center justify-between gap-5 rounded-3xl bg-slate-900 px-6 py-10 text-center text-white sm:flex-row sm:px-10 sm:text-left">
            <div>
              <h2 className="text-2xl font-extrabold">
                Ready to explore more?
              </h2>
              <p className="mt-2 text-sm text-slate-300">
                Browse our complete collection of products.
              </p>
            </div>

            <button
              onClick={() => navigate('/shop')}
              className="flex shrink-0 items-center gap-2 rounded-xl bg-blue-600 px-6 py-3 font-bold transition hover:bg-blue-500"
            >
              View All Products
              <ArrowRight size={18} />
            </button>
          </section>
        </>
      )}
    </div>
  );
}
