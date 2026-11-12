
import { useEffect, useMemo, useState } from 'react';
import {
  Search,
  RefreshCw,
  Package,
  Plus,
  X,
  Loader2,
  Pencil,
  Trash2,
  Image as ImageIcon,
  Boxes,
  CheckCircle2,
  AlertCircle,
  Filter,
  Tag,
} from 'lucide-react';

import api from '../services/api';

const emptyForm = {
  name: '',
  sku: '',
  price: '',
  category: '',
  description: '',
  brand: '',
  image_url: '',
};

const formatCurrency = (value) =>
  `₹${Number(value ?? 0).toLocaleString('en-IN', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;

function ProductImage({ src, name, large = false }) {
  const [failed, setFailed] = useState(false);

  const imageSize = large ? 'h-24 w-24' : 'h-14 w-14';

  if (!src || failed) {
    return (
      <div className={`${imageSize} flex shrink-0 items-center justify-center rounded-xl bg-slate-100 text-slate-400`}>
        <ImageIcon size={large ? 30 : 22} />
      </div>
    );
  }

  return (
    <img
      src={src}
      alt={name || 'Product'}
      loading="lazy"
      onError={() => setFailed(true)}
      className={`${imageSize} shrink-0 rounded-xl border border-slate-100 bg-slate-50 object-cover`}
    />
  );
}

function ProductSkeleton() {
  return (
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
      {Array.from({ length: 6 }).map((_, index) => (
        <div
          key={index}
          className="animate-pulse rounded-2xl border border-slate-200 bg-white p-5"
        >
          <div className="flex gap-4">
            <div className="h-16 w-16 rounded-xl bg-slate-200" />
            <div className="flex-1 space-y-3">
              <div className="h-4 w-3/4 rounded bg-slate-200" />
              <div className="h-3 w-1/2 rounded bg-slate-200" />
            </div>
          </div>
          <div className="mt-6 h-4 w-1/3 rounded bg-slate-200" />
          <div className="mt-5 h-9 rounded bg-slate-200" />
        </div>
      ))}
    </div>
  );
}

export default function Products({ isAdmin = false }) {
  const [products, setProducts] = useState([]);
  const [search, setSearch] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('All');

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const [showForm, setShowForm] = useState(false);
  const [editingProduct, setEditingProduct] = useState(null);
  const [form, setForm] = useState(emptyForm);

  const [saving, setSaving] = useState(false);
  const [deletingId, setDeletingId] = useState(null);
  const [formError, setFormError] = useState('');
  const [success, setSuccess] = useState('');

  async function loadProducts() {
    setLoading(true);
    setError('');

    try {
      const endpoint = isAdmin ? '/products/admin/all' : '/products';
      const response = await api.get(endpoint);
      setProducts(Array.isArray(response.data) ? response.data : []);
    } catch (err) {
      setError(
        err.response?.data?.detail ||
        'Unable to load products. Please try again.'
      );
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadProducts();
  }, [isAdmin]);

  function handleFormChange(event) {
    const { name, value } = event.target;

    setForm((previous) => ({
      ...previous,
      [name]: value,
    }));
  }

  function openAddForm() {
    setEditingProduct(null);
    setForm(emptyForm);
    setFormError('');
    setSuccess('');
    setShowForm(true);
  }

  function openEditForm(product) {
    setEditingProduct(product);

    setForm({
      name: product.name ?? '',
      sku: product.sku ?? '',
      price: String(product.price ?? ''),
      category: product.category ?? '',
      description: product.description ?? '',
      brand: product.brand ?? '',
      image_url: product.image_url ?? '',
    });

    setFormError('');
    setSuccess('');
    setShowForm(true);
  }

  function closeForm() {
    if (saving) return;

    setShowForm(false);
    setEditingProduct(null);
    setForm(emptyForm);
    setFormError('');
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setFormError('');
    setSuccess('');

    if (
      !form.name.trim() ||
      !form.sku.trim() ||
      !form.category.trim() ||
      !form.price
    ) {
      setFormError('Please complete all required fields.');
      return;
    }

    const price = Number(form.price);

    if (!Number.isFinite(price) || price <= 0) {
      setFormError('Price must be greater than zero.');
      return;
    }

    const productData = {
      name: form.name.trim(),
      sku: form.sku.trim(),
      price,
      category: form.category.trim(),
      description: form.description.trim() || null,
      brand: form.brand.trim() || null,
      image_url: form.image_url.trim() || null,
    };

    setSaving(true);

    try {
      if (editingProduct) {
        await api.put(
          `/products/${editingProduct.id}`,
          productData
        );

        setSuccess('Product updated successfully.');
      } else {
        await api.post('/products', productData);
        setSuccess('Product added successfully.');
      }

      setShowForm(false);
      setEditingProduct(null);
      setForm(emptyForm);

      await loadProducts();
    } catch (err) {
      const detail = err.response?.data?.detail;

      setFormError(
        Array.isArray(detail)
          ? detail.map((item) => item.msg).join(', ')
          : detail || 'Unable to save product. Please try again.'
      );
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(product) {
    const confirmed = window.confirm(
      `Are you sure you want to deactivate "${product.name}"?`
    );

    if (!confirmed) return;

    setDeletingId(product.id);
    setError('');
    setSuccess('');

    try {
      await api.delete(`/products/${product.id}`);
      setSuccess('Product deactivated successfully.');
      await loadProducts();
    } catch (err) {
      const detail = err.response?.data?.detail;

      setError(
        typeof detail === 'string'
          ? detail
          : 'Unable to deactivate product. Please try again.'
      );
    } finally {
      setDeletingId(null);
    }
  }

  const categories = useMemo(() => {
    const values = products
      .map((product) => product.category)
      .filter(Boolean);

    return ['All', ...new Set(values)].sort((a, b) => {
      if (a === 'All') return -1;
      return String(a).localeCompare(String(b));
    });
  }, [products]);

  const filteredProducts = products.filter((product) => {
    const query = search.trim().toLowerCase();

    const matchesSearch =
      String(product.name ?? '').toLowerCase().includes(query) ||
      String(product.id ?? '').includes(query) ||
      String(product.sku ?? '').toLowerCase().includes(query) ||
      String(product.category ?? '').toLowerCase().includes(query) ||
      String(product.brand ?? '').toLowerCase().includes(query);

    const matchesCategory =
      selectedCategory === 'All' ||
      product.category === selectedCategory;

    return matchesSearch && matchesCategory;
  });

  const activeProducts = products.filter(
    (product) => product.is_active
  ).length;

  const inactiveProducts = products.length - activeProducts;

  return (
    <section className="page-enter space-y-6 p-5 md:p-8">

      {/* Page heading */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <p className="text-sm font-semibold uppercase tracking-wider text-blue-600">
            Catalog management
          </p>
          <h1 className="mt-1 text-2xl font-bold text-slate-900 md:text-3xl">
            Products
          </h1>
          <p className="mt-2 text-sm text-slate-500">
            Manage your product catalog, pricing, and availability.
          </p>
        </div>

        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={loadProducts}
            disabled={loading}
            className="flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-semibold text-slate-600 shadow-sm hover:bg-slate-50 disabled:opacity-50"
          >
            <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
            Refresh
          </button>

          <button
            type="button"
            onClick={openAddForm}
            className="flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white shadow-lg shadow-blue-600/20 hover:bg-blue-700"
          >
            <Plus size={17} />
            Add Product
          </button>
        </div>
      </div>

      {/* Notifications */}
      {success && (
        <div
          role="status"
          className="flex items-center gap-3 rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-700"
        >
          <CheckCircle2 size={19} />
          {success}
          <button
            type="button"
            onClick={() => setSuccess('')}
            className="ml-auto rounded p-1 hover:bg-emerald-100"
            aria-label="Dismiss success message"
          >
            <X size={16} />
          </button>
        </div>
      )}

      {error && (
        <div
          role="alert"
          className="flex items-start gap-3 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700"
        >
          <AlertCircle size={19} className="mt-0.5 shrink-0" />
          <span>{error}</span>
          <button
            type="button"
            onClick={() => setError('')}
            className="ml-auto rounded p-1 hover:bg-red-100"
            aria-label="Dismiss error message"
          >
            <X size={16} />
          </button>
        </div>
      )}

      {/* Statistics */}
      <div className="grid gap-4 sm:grid-cols-3">
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-slate-500">Total products</p>
              <p className="mt-2 text-3xl font-bold text-slate-900">
                {products.length}
              </p>
            </div>
            <div className="rounded-xl bg-blue-50 p-3 text-blue-600">
              <Package size={23} />
            </div>
          </div>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-slate-500">Active products</p>
              <p className="mt-2 text-3xl font-bold text-emerald-600">
                {activeProducts}
              </p>
            </div>
            <div className="rounded-xl bg-emerald-50 p-3 text-emerald-600">
              <CheckCircle2 size={23} />
            </div>
          </div>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-slate-500">Inactive products</p>
              <p className="mt-2 text-3xl font-bold text-slate-600">
                {inactiveProducts}
              </p>
            </div>
            <div className="rounded-xl bg-slate-100 p-3 text-slate-500">
              <Boxes size={23} />
            </div>
          </div>
        </div>
      </div>

      {/* Add/Edit product form */}
      {showForm && (
        <div className="rounded-2xl border border-blue-100 bg-white p-5 shadow-lg md:p-7">
          <div className="mb-6 flex items-start justify-between gap-3">
            <div>
              <p className="text-sm font-semibold text-blue-600">
                Product catalog
              </p>
              <h2 className="mt-1 text-xl font-bold text-slate-900">
                {editingProduct ? 'Edit Product' : 'Add New Product'}
              </h2>
              <p className="mt-1 text-sm text-slate-500">
                Fields marked with * are required.
              </p>
            </div>

            <button
              type="button"
              onClick={closeForm}
              disabled={saving}
              className="rounded-xl p-2 text-slate-500 hover:bg-slate-100"
              aria-label="Close form"
            >
              <X size={21} />
            </button>
          </div>

          <form onSubmit={handleSubmit} className="space-y-5">
            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <label htmlFor="product-name" className="mb-2 block text-sm font-semibold text-slate-700">
                  Product Name *
                </label>
                <input
                  id="product-name"
                  name="name"
                  value={form.name}
                  onChange={handleFormChange}
                  minLength={2}
                  maxLength={150}
                  required
                  disabled={saving}
                  placeholder="Enter product name"
                  className="w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm outline-none transition focus:border-blue-500 focus:bg-white focus:ring-4 focus:ring-blue-50"
                />
              </div>

              <div>
                <label htmlFor="product-sku" className="mb-2 block text-sm font-semibold text-slate-700">
                  SKU *
                </label>
                <input
                  id="product-sku"
                  name="sku"
                  value={form.sku}
                  onChange={handleFormChange}
                  minLength={2}
                  maxLength={50}
                  required
                  disabled={saving}
                  placeholder="Example: PROD-001"
                  className="w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm outline-none transition focus:border-blue-500 focus:bg-white focus:ring-4 focus:ring-blue-50"
                />
              </div>

              <div>
                <label htmlFor="product-price" className="mb-2 block text-sm font-semibold text-slate-700">
                  Price (₹) *
                </label>
                <input
                  id="product-price"
                  type="number"
                  name="price"
                  value={form.price}
                  onChange={handleFormChange}
                  min="0.01"
                  step="0.01"
                  required
                  disabled={saving}
                  placeholder="Enter price"
                  className="w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm outline-none transition focus:border-blue-500 focus:bg-white focus:ring-4 focus:ring-blue-50"
                />
              </div>

              <div>
                <label htmlFor="product-category" className="mb-2 block text-sm font-semibold text-slate-700">
                  Category *
                </label>
                <input
                  id="product-category"
                  name="category"
                  value={form.category}
                  onChange={handleFormChange}
                  minLength={2}
                  maxLength={100}
                  required
                  disabled={saving}
                  placeholder="Example: Electronics"
                  className="w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm outline-none transition focus:border-blue-500 focus:bg-white focus:ring-4 focus:ring-blue-50"
                />
              </div>

              <div>
                <label htmlFor="product-brand" className="mb-2 block text-sm font-semibold text-slate-700">
                  Brand
                </label>
                <input
                  id="product-brand"
                  name="brand"
                  value={form.brand}
                  onChange={handleFormChange}
                  maxLength={100}
                  disabled={saving}
                  placeholder="Enter brand"
                  className="w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm outline-none transition focus:border-blue-500 focus:bg-white focus:ring-4 focus:ring-blue-50"
                />
              </div>

              <div>
                <label htmlFor="product-image" className="mb-2 block text-sm font-semibold text-slate-700">
                  Image URL
                </label>
                <input
                  id="product-image"
                  name="image_url"
                  type="url"
                  value={form.image_url}
                  onChange={handleFormChange}
                  maxLength={500}
                  disabled={saving}
                  placeholder="https://example.com/image.jpg"
                  className="w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm outline-none transition focus:border-blue-500 focus:bg-white focus:ring-4 focus:ring-blue-50"
                />
              </div>
            </div>

            {/* Image preview */}
            {form.image_url && (
              <div className="flex items-center gap-4 rounded-xl border border-slate-200 bg-slate-50 p-4">
                <ProductImage
                  src={form.image_url}
                  name={form.name}
                  large
                />
                <div className="min-w-0">
                  <p className="text-sm font-semibold text-slate-700">
                    Image preview
                  </p>
                  <p className="mt-1 break-all text-xs text-slate-500">
                    {form.image_url}
                  </p>
                </div>
              </div>
            )}

            <div>
              <label htmlFor="product-description" className="mb-2 block text-sm font-semibold text-slate-700">
                Description
              </label>
              <textarea
                id="product-description"
                name="description"
                value={form.description}
                onChange={handleFormChange}
                rows={4}
                disabled={saving}
                placeholder="Describe the product..."
                className="w-full resize-y rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm outline-none transition focus:border-blue-500 focus:bg-white focus:ring-4 focus:ring-blue-50"
              />
            </div>

            {formError && (
              <div role="alert" className="flex items-start gap-2 rounded-xl bg-red-50 p-3 text-sm text-red-700">
                <AlertCircle size={18} className="mt-0.5 shrink-0" />
                {formError}
              </div>
            )}

            <div className="flex flex-wrap justify-end gap-3 border-t border-slate-100 pt-5">
              <button
                type="button"
                onClick={closeForm}
                disabled={saving}
                className="rounded-xl border border-slate-200 px-5 py-3 text-sm font-semibold text-slate-600 hover:bg-slate-50"
              >
                Cancel
              </button>

              <button
                type="submit"
                disabled={saving}
                className="flex items-center gap-2 rounded-xl bg-blue-600 px-6 py-3 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-60"
              >
                {saving ? (
                  <Loader2 size={17} className="animate-spin" />
                ) : (
                  <Plus size={17} />
                )}
                {saving
                  ? 'Saving...'
                  : editingProduct
                    ? 'Update Product'
                    : 'Save Product'}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Search and filters */}
      <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
        <div className="flex flex-col gap-4 md:flex-row">
          <div className="flex flex-1 items-center gap-3 rounded-xl border border-slate-200 bg-slate-50 px-4 focus-within:border-blue-500 focus-within:bg-white">
            <Search size={19} className="shrink-0 text-slate-400" />
            <input
              type="search"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search name, SKU, brand or category..."
              className="w-full bg-transparent py-3 text-sm outline-none"
            />
          </div>

          <div className="flex items-center gap-2 rounded-xl border border-slate-200 bg-slate-50 px-3">
            <Filter size={17} className="shrink-0 text-slate-400" />
            <select
              value={selectedCategory}
              onChange={(event) => setSelectedCategory(event.target.value)}
              className="w-full min-w-32 bg-transparent py-3 text-sm outline-none"
              aria-label="Filter by category"
            >
              {categories.map((category) => (
                <option key={category} value={category}>
                  {category === 'All' ? 'All Categories' : category}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="mt-3 flex items-center justify-between gap-3 text-xs text-slate-500">
          <span>
            Showing {filteredProducts.length} of {products.length} products
          </span>
          {(search || selectedCategory !== 'All') && (
            <button
              type="button"
              onClick={() => {
                setSearch('');
                setSelectedCategory('All');
              }}
              className="font-semibold text-blue-600 hover:text-blue-800"
            >
              Clear filters
            </button>
          )}
        </div>
      </div>

      {/* Product list */}
      {loading ? (
        <ProductSkeleton />
      ) : filteredProducts.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-slate-300 bg-white px-6 py-14 text-center">
          <Package size={40} className="mx-auto text-slate-300" />
          <h3 className="mt-4 font-bold text-slate-800">
            No products found
          </h3>
          <p className="mt-2 text-sm text-slate-500">
            Try changing your search or category filter.
          </p>
          <button
            type="button"
            onClick={openAddForm}
            className="mt-5 inline-flex items-center gap-2 rounded-xl bg-blue-600 px-5 py-3 text-sm font-semibold text-white hover:bg-blue-700"
          >
            <Plus size={17} />
            Add your first product
          </button>
        </div>
      ) : (
        <>
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-bold text-slate-900">
              Product Catalog
            </h2>
            <span className="text-xs text-slate-500">
              {filteredProducts.length} results
            </span>
          </div>

          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
            {filteredProducts.map((product) => (
              <article
                key={product.id}
                className="group rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition duration-200 hover:-translate-y-1 hover:shadow-lg"
              >
                <div className="flex items-start gap-4">
                  <ProductImage
                    src={product.image_url}
                    name={product.name}
                    large
                  />

                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span
                        className={`rounded-full px-2.5 py-1 text-xs font-semibold ${
                          product.is_active
                            ? 'bg-emerald-50 text-emerald-700'
                            : 'bg-slate-100 text-slate-600'
                        }`}
                      >
                        {product.is_active ? 'Active' : 'Inactive'}
                      </span>
                    </div>

                    <h3 className="mt-2 break-words font-bold text-slate-900">
                      {product.name || 'Unnamed product'}
                    </h3>

                    <p className="mt-1 text-xs text-slate-500">
                      SKU: {product.sku || 'N/A'}
                    </p>
                  </div>
                </div>

                <div className="mt-5 flex items-center justify-between gap-3 border-t border-slate-100 pt-4">
                  <div className="min-w-0">
                    <p className="text-xl font-bold text-blue-700">
                      {formatCurrency(product.price)}
                    </p>
                    <p className="mt-1 flex items-center gap-1.5 text-xs text-slate-500">
                      <Tag size={13} />
                      {product.category || 'Uncategorized'}
                    </p>
                    {product.brand && (
                      <p className="mt-1 truncate text-xs text-slate-400">
                        Brand: {product.brand}
                      </p>
                    )}
                  </div>

                  <span className="shrink-0 rounded-lg bg-slate-50 px-3 py-2 text-xs font-medium text-slate-500">
                    ID #{product.id}
                  </span>
                </div>

                {product.description && (
                  <p className="mt-3 line-clamp-2 text-sm leading-5 text-slate-500">
                    {product.description}
                  </p>
                )}

                <div className="mt-5 flex gap-2 border-t border-slate-100 pt-4">
                  {product.is_active ? (
                    <>
                      <button
                        type="button"
                        onClick={() => openEditForm(product)}
                        className="flex flex-1 items-center justify-center gap-2 rounded-xl border border-blue-200 py-2.5 text-sm font-semibold text-blue-600 hover:bg-blue-50"
                      >
                        <Pencil size={16} />
                        Edit
                      </button>

                      <button
                        type="button"
                        onClick={() => handleDelete(product)}
                        disabled={deletingId === product.id}
                        title="Deactivate product"
                        className="flex flex-1 items-center justify-center gap-2 rounded-xl border border-red-200 py-2.5 text-sm font-semibold text-red-600 hover:bg-red-50 disabled:cursor-not-allowed disabled:opacity-40"
                      >
                        {deletingId === product.id ? (
                          <Loader2 size={16} className="animate-spin" />
                        ) : (
                          <Trash2 size={16} />
                        )}
                        Deactivate
                      </button>
                    </>
                  ) : (
                    <div className="w-full rounded-xl bg-slate-100 px-4 py-2.5 text-center text-sm font-semibold text-slate-500">
                      Product is inactive
                    </div>
                  )}
                </div>

              </article>
            ))}
          </div>
        </>
      )}
    </section>
  );
}
