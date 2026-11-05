
import { useEffect, useMemo, useState } from 'react';
import {
  RefreshCw,
  Boxes,
  AlertTriangle,
  PackageCheck,
  Package,
  Search,
  Clock,
  TrendingDown,
  CheckCircle2,
  XCircle,
  Plus,
  PackagePlus,
} from 'lucide-react';
import api from '../services/api';

function formatDate(value) {
  if (!value) return 'Not available';

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) return 'Not available';

  return date.toLocaleString('en-IN', {
    dateStyle: 'medium',
    timeStyle: 'short',
  });
}

function StockBadge({ quantity }) {
  const value = Number(quantity) || 0;

  if (value === 0) {
    return (
      <span className="inline-flex items-center gap-1.5 rounded-full bg-red-50 px-3 py-1.5 text-xs font-semibold text-red-700">
        <XCircle size={13} />
        Out of stock
      </span>
    );
  }

  if (value <= 10) {
    return (
      <span className="inline-flex items-center gap-1.5 rounded-full bg-amber-50 px-3 py-1.5 text-xs font-semibold text-amber-700">
        <AlertTriangle size={13} />
        Low stock
      </span>
    );
  }

  return (
    <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-50 px-3 py-1.5 text-xs font-semibold text-emerald-700">
      <CheckCircle2 size={13} />
      In stock
    </span>
  );
}

function StatCard({ title, value, description, icon: Icon, color }) {
  const colors = {
    blue: 'bg-blue-50 text-blue-600',
    green: 'bg-emerald-50 text-emerald-600',
    amber: 'bg-amber-50 text-amber-600',
    red: 'bg-red-50 text-red-600',
  };

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition duration-200 hover:-translate-y-1 hover:shadow-md">
      <div className="flex items-center justify-between">
        <p className="text-sm font-medium text-slate-500">{title}</p>
        <div className={`rounded-xl p-3 ${colors[color]}`}>
          <Icon size={21} />
        </div>
      </div>

      <p className="mt-4 text-3xl font-bold tracking-tight text-slate-900">
        {value}
      </p>

      <p className="mt-1 text-xs text-slate-400">{description}</p>
    </div>
  );
}

function LoadingSkeleton() {
  return (
    <div className="space-y-3 p-5">
      {[1, 2, 3, 4, 5].map((item) => (
        <div
          key={item}
          className="h-14 animate-pulse rounded-xl bg-slate-100"
        />
      ))}
    </div>
  );
}

export default function Inventory() {
  const [inventory, setInventory] = useState([]);
  const [lowStock, setLowStock] = useState([]);
  const [products, setProducts] = useState([]);

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const [search, setSearch] = useState('');
  const [stockFilter, setStockFilter] = useState('all');

  const [selectedProduct, setSelectedProduct] = useState('');
  const [quantity, setQuantity] = useState('');

  async function loadInventory() {
    setLoading(true);
    setError('');

    try {
      const [
        inventoryResponse,
        lowStockResponse,
        productsResponse,
      ] = await Promise.all([
        api.get('/inventory'),
        api.get('/inventory/low-stock'),
        api.get('/products'),
      ]);

      setInventory(
        Array.isArray(inventoryResponse.data)
          ? inventoryResponse.data
          : []
      );

      setLowStock(
        Array.isArray(lowStockResponse.data)
          ? lowStockResponse.data
          : []
      );

      setProducts(
        Array.isArray(productsResponse.data)
          ? productsResponse.data
          : []
      );
    } catch (err) {
      setError(
        err.response?.data?.detail ||
        'Unable to load inventory. Please try again.'
      );
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadInventory();
  }, []);

  const selectedInventory = inventory.find(
    (item) => Number(item.product_id) === Number(selectedProduct)
  );

  const selectedProductDetails = products.find(
    (product) => Number(product.id) === Number(selectedProduct)
  );

  async function handleAddStock(event) {
    event.preventDefault();

    setError('');
    setSuccess('');

    const productId = Number(selectedProduct);
    const stockQuantity = Number(quantity);

    if (!productId || !Number.isInteger(productId)) {
      setError('Please select a valid product.');
      return;
    }

    if (
      !Number.isInteger(stockQuantity) ||
      stockQuantity <= 0
    ) {
      setError('Please enter a valid positive whole-number quantity.');
      return;
    }

    setSaving(true);

    try {
      if (selectedInventory) {
        await api.post('/inventory/movements', {
          product_id: productId,
          quantity_change: stockQuantity,
          reason: 'Stock added from Inventory Management',
        });

        setSuccess(
          `Successfully added ${stockQuantity} units to ${selectedProductDetails?.name || `Product #${productId}`}.`
        );
      } else {
        await api.post('/inventory', {
          product_id: productId,
          quantity: stockQuantity,
        });

        setSuccess(
          `Inventory created successfully with ${stockQuantity} units for ${selectedProductDetails?.name || `Product #${productId}`}.`
        );
      }

      setQuantity('');
      await loadInventory();
    } catch (err) {
      setError(
        err.response?.data?.detail ||
        'Unable to update stock. Please try again.'
      );
    } finally {
      setSaving(false);
    }
  }

  const totalUnits = inventory.reduce(
    (total, item) => total + (Number(item.quantity) || 0),
    0
  );

  const outOfStock = inventory.filter(
    (item) => Number(item.quantity) === 0
  ).length;

  const filteredInventory = useMemo(() => {
    return inventory.filter((item) => {
      const quantityValue = Number(item.quantity) || 0;
      const searchValue = search.trim().toLowerCase();

      const matchesSearch =
        !searchValue ||
        String(item.product_id).toLowerCase().includes(searchValue) ||
        String(item.id).toLowerCase().includes(searchValue);

      let matchesFilter = true;

      if (stockFilter === 'low') {
        matchesFilter =
          quantityValue > 0 && quantityValue <= 10;
      } else if (stockFilter === 'out') {
        matchesFilter = quantityValue === 0;
      } else if (stockFilter === 'available') {
        matchesFilter = quantityValue > 10;
      }

      return matchesSearch && matchesFilter;
    });
  }, [inventory, search, stockFilter]);

  return (
    <section className="min-h-screen space-y-7 p-4 md:p-7">

      {/* Page heading */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="mb-2 flex items-center gap-2 text-sm font-medium text-blue-600">
            <Boxes size={16} />
            Inventory Management
          </div>

          <h1 className="text-3xl font-bold tracking-tight text-slate-900">
            Inventory
          </h1>

          <p className="mt-2 text-sm text-slate-500">
            Monitor stock levels and manage product replenishment.
          </p>
        </div>

        <button
          type="button"
          onClick={loadInventory}
          disabled={loading || saving}
          className="inline-flex items-center gap-2 rounded-xl bg-slate-900 px-5 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-50"
        >
          <RefreshCw
            size={16}
            className={loading ? 'animate-spin' : ''}
          />
          {loading ? 'Refreshing...' : 'Refresh Stock'}
        </button>
      </div>

      {/* Add stock form */}
      <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm md:p-6">
        <div className="mb-5 flex items-center gap-3">
          <div className="rounded-xl bg-blue-50 p-3 text-blue-600">
            <PackagePlus size={22} />
          </div>

          <div>
            <h2 className="text-lg font-bold text-slate-900">
              Add Product Stock
            </h2>
            <p className="text-sm text-slate-500">
              Create inventory for a product or replenish existing stock.
            </p>
          </div>
        </div>

        <form
          onSubmit={handleAddStock}
          className="grid gap-4 md:grid-cols-3"
        >
          <div>
            <label
              htmlFor="inventory-product"
              className="mb-2 block text-sm font-semibold text-slate-700"
            >
              Select product
            </label>

            <select
              id="inventory-product"
              value={selectedProduct}
              onChange={(event) => {
                setSelectedProduct(event.target.value);
                setError('');
                setSuccess('');
              }}
              disabled={saving || loading}
              required
              className="w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm outline-none transition focus:border-blue-400 focus:bg-white focus:ring-4 focus:ring-blue-50 disabled:opacity-50"
            >
              <option value="">Choose a product</option>

              {products.map((product) => (
                <option key={product.id} value={product.id}>
                  {product.name} (ID: {product.id})
                  {product.is_active === false ? ' - Inactive' : ''}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label
              htmlFor="stock-quantity"
              className="mb-2 block text-sm font-semibold text-slate-700"
            >
              Quantity to add
            </label>

            <input
              id="stock-quantity"
              type="number"
              min="1"
              step="1"
              value={quantity}
              onChange={(event) => setQuantity(event.target.value)}
              placeholder="Enter quantity"
              disabled={saving}
              required
              className="w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm outline-none transition focus:border-blue-400 focus:bg-white focus:ring-4 focus:ring-blue-50 disabled:opacity-50"
            />
          </div>

          <div className="flex items-end">
            <button
              type="submit"
              disabled={saving || loading || !selectedProduct}
              className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-blue-600 px-5 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {saving ? (
                <>
                  <RefreshCw size={16} className="animate-spin" />
                  Saving...
                </>
              ) : (
                <>
                  <Plus size={17} />
                  Add Stock
                </>
              )}
            </button>
          </div>
        </form>

        {selectedProduct && (
          <div className="mt-4 rounded-xl bg-slate-50 p-4 text-sm">
            <p className="font-semibold text-slate-700">
              {selectedProductDetails?.name || `Product #${selectedProduct}`}
            </p>

            <p className="mt-1 text-slate-500">
              {selectedInventory
                ? `Current stock: ${selectedInventory.quantity} units. The entered quantity will be added to existing stock.`
                : 'No inventory record exists. A new inventory record will be created.'}
            </p>
          </div>
        )}
      </div>

      {/* Success message */}
      {success && (
        <div
          role="status"
          className="flex items-center gap-2 rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-700"
        >
          <CheckCircle2 size={18} />
          {success}
        </div>
      )}

      {/* Error message */}
      {error && (
        <div
          role="alert"
          className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700"
        >
          <div className="flex items-center gap-2">
            <AlertTriangle size={18} />
            {error}
          </div>

          <button
            type="button"
            onClick={loadInventory}
            className="font-semibold underline"
          >
            Try again
          </button>
        </div>
      )}

      {/* Statistics */}
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard
          title="Tracked products"
          value={loading ? '—' : inventory.length.toLocaleString('en-IN')}
          description="Products with inventory records"
          icon={Boxes}
          color="blue"
        />

        <StatCard
          title="Total units"
          value={loading ? '—' : totalUnits.toLocaleString('en-IN')}
          description="Combined available stock"
          icon={PackageCheck}
          color="green"
        />

        <StatCard
          title="Low stock"
          value={loading ? '—' : lowStock.length.toLocaleString('en-IN')}
          description="Products at or below 10 units"
          icon={TrendingDown}
          color="amber"
        />

        <StatCard
          title="Out of stock"
          value={loading ? '—' : outOfStock.toLocaleString('en-IN')}
          description="Products with zero units"
          icon={AlertTriangle}
          color="red"
        />
      </div>

      {/* Stock levels */}
      <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-100 p-5 md:p-6">
          <div>
            <h2 className="text-lg font-bold text-slate-900">
              Stock levels
            </h2>
            <p className="mt-1 text-sm text-slate-500">
              Current quantities from the Inventory Service.
            </p>
          </div>

          <span className="rounded-full bg-blue-50 px-3 py-1.5 text-xs font-semibold text-blue-700">
            {loading ? 'Loading...' : `${filteredInventory.length} records`}
          </span>
        </div>

        {/* Search and filters */}
        <div className="flex flex-col gap-3 border-b border-slate-100 p-4 md:flex-row md:items-center md:justify-between">
          <div className="relative w-full md:max-w-sm">
            <Search
              size={17}
              className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"
            />

            <input
              type="text"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search product ID..."
              className="w-full rounded-xl border border-slate-200 bg-slate-50 py-2.5 pl-10 pr-4 text-sm outline-none transition focus:border-blue-400 focus:bg-white focus:ring-4 focus:ring-blue-50"
            />
          </div>

          <div className="flex flex-wrap gap-2">
            {[
              { value: 'all', label: 'All stock' },
              { value: 'available', label: 'In stock' },
              { value: 'low', label: 'Low stock' },
              { value: 'out', label: 'Out of stock' },
            ].map((filter) => (
              <button
                key={filter.value}
                type="button"
                onClick={() => setStockFilter(filter.value)}
                className={`rounded-lg px-3 py-2 text-xs font-semibold transition ${
                  stockFilter === filter.value
                    ? 'bg-slate-900 text-white shadow-sm'
                    : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                }`}
              >
                {filter.label}
              </button>
            ))}
          </div>
        </div>

        {loading ? (
          <LoadingSkeleton />
        ) : !error && filteredInventory.length === 0 ? (
          <div className="px-5 py-16 text-center">
            <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-slate-100 text-slate-400">
              <Package size={26} />
            </div>

            <h3 className="mt-4 font-semibold text-slate-800">
              {inventory.length === 0
                ? 'No inventory records found'
                : 'No matching products'}
            </h3>

            <p className="mt-1 text-sm text-slate-500">
              {inventory.length === 0
                ? 'Add stock using the form above to create inventory records.'
                : 'Try changing your search or stock filter.'}
            </p>

            {(search || stockFilter !== 'all') && (
              <button
                type="button"
                onClick={() => {
                  setSearch('');
                  setStockFilter('all');
                }}
                className="mt-4 text-sm font-semibold text-blue-600 hover:text-blue-700"
              >
                Clear filters
              </button>
            )}
          </div>
        ) : (
          !error && (
            <>
              {/* Desktop table */}
              <div className="hidden overflow-x-auto md:block">
                <table className="w-full text-left text-sm">
                  <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
                    <tr>
                      <th className="px-6 py-4 font-semibold">Product ID</th>
                      <th className="px-6 py-4 font-semibold">Quantity</th>
                      <th className="px-6 py-4 font-semibold">Stock status</th>
                      <th className="px-6 py-4 font-semibold">Last updated</th>
                    </tr>
                  </thead>

                  <tbody className="divide-y divide-slate-100">
                    {filteredInventory.map((item) => (
                      <tr
                        key={item.id ?? item.product_id}
                        className="transition hover:bg-slate-50"
                      >
                        <td className="px-6 py-4">
                          <span className="font-semibold text-slate-800">
                            #{item.product_id}
                          </span>
                        </td>

                        <td className="px-6 py-4">
                          <span className="font-bold text-slate-900">
                            {Number(item.quantity) || 0}
                          </span>
                          <span className="ml-1 text-xs text-slate-400">
                            units
                          </span>
                        </td>

                        <td className="px-6 py-4">
                          <StockBadge quantity={item.quantity} />
                        </td>

                        <td className="px-6 py-4 text-slate-500">
                          <span className="inline-flex items-center gap-2">
                            <Clock size={14} />
                            {formatDate(item.updated_at)}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Mobile cards */}
              <div className="space-y-3 p-4 md:hidden">
                {filteredInventory.map((item) => (
                  <div
                    key={item.id ?? item.product_id}
                    className="rounded-xl border border-slate-200 p-4"
                  >
                    <div className="flex items-center justify-between gap-3">
                      <span className="font-semibold text-slate-800">
                        Product #{item.product_id}
                      </span>

                      <StockBadge quantity={item.quantity} />
                    </div>

                    <div className="mt-4 flex items-end justify-between">
                      <div>
                        <p className="text-xs text-slate-500">
                          Available quantity
                        </p>
                        <p className="mt-1 text-2xl font-bold text-slate-900">
                          {Number(item.quantity) || 0}
                          <span className="ml-1 text-xs font-medium text-slate-400">
                            units
                          </span>
                        </p>
                      </div>
                    </div>

                    <div className="mt-4 flex items-center gap-2 border-t border-slate-100 pt-3 text-xs text-slate-500">
                      <Clock size={13} />
                      Updated: {formatDate(item.updated_at)}
                    </div>
                  </div>
                ))}
              </div>
            </>
          )
        )}

        {/* Footer */}
        {!loading && !error && inventory.length > 0 && (
          <div className="border-t border-slate-100 bg-slate-50 px-5 py-3 text-xs text-slate-500">
            Showing {filteredInventory.length} of {inventory.length} inventory records.
          </div>
        )}
      </div>
    </section>
  );
}
