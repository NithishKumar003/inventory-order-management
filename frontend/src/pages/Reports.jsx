import { useCallback, useEffect, useState } from 'react';
import {
  Activity,
  AlertTriangle,
  BarChart3,
  Boxes,
  CreditCard,
  DollarSign,
  Package,
  RefreshCw,
  RotateCcw,
  ShoppingCart,
  TrendingUp,
} from 'lucide-react';

import api from '../services/api';

const REPORT_ENDPOINTS = {
  overview: 'overview',
  sales: 'sales',
  inventory: 'inventory',
  payments: 'payments',
  returns: 'returns',
  products: 'products',
};

function formatCurrency(value) {
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 2,
  }).format(Number(value || 0));
}

function formatNumber(value) {
  return new Intl.NumberFormat('en-IN').format(Number(value || 0));
}

function MetricCard({ title, value, icon: Icon, color, description }) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-medium text-gray-500">{title}</p>
          <h3 className="mt-2 text-2xl font-bold text-gray-900">
            {value}
          </h3>
          {description && (
            <p className="mt-1 text-xs text-gray-500">{description}</p>
          )}
        </div>

        <div className={`rounded-xl p-3 ${color}`}>
          <Icon size={23} />
        </div>
      </div>
    </div>
  );
}

function ReportSection({ title, subtitle, children }) {
  return (
    <section className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
      <div className="mb-5">
        <h2 className="text-lg font-bold text-gray-900">{title}</h2>
        {subtitle && (
          <p className="mt-1 text-sm text-gray-500">{subtitle}</p>
        )}
      </div>
      {children}
    </section>
  );
}

function BreakdownList({ data, currency = false }) {
  const entries = Object.entries(data || {});
  const maximum = Math.max(
    ...entries.map(([, value]) => Number(value || 0)),
    1
  );

  if (entries.length === 0) {
    return (
      <p className="text-sm text-gray-500">No data available yet.</p>
    );
  }

  return (
    <div className="space-y-4">
      {entries.map(([label, value]) => (
        <div key={label}>
          <div className="mb-1 flex justify-between gap-3 text-sm">
            <span className="font-medium capitalize text-gray-700">
              {label.replaceAll('_', ' ')}
            </span>
            <span className="font-semibold text-gray-900">
              {currency
                ? formatCurrency(value)
                : formatNumber(value)}
            </span>
          </div>

          <div className="h-2 overflow-hidden rounded-full bg-gray-100">
            <div
              className="h-full rounded-full bg-indigo-500"
              style={{
                width: `${Math.min(
                  (Number(value || 0) / maximum) * 100,
                  100
                )}%`,
              }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}

function EmptyState({ message }) {
  return (
    <div className="rounded-lg bg-gray-50 p-6 text-center text-sm text-gray-500">
      {message}
    </div>
  );
}

export default function Reports() {
  const [reports, setReports] = useState({});
  const [errors, setErrors] = useState({});
  const [loading, setLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState(null);

  const loadReports = useCallback(async () => {
    setLoading(true);

    const results = await Promise.all(
      Object.entries(REPORT_ENDPOINTS).map(
        async ([reportName, endpoint]) => {
          try {
            const response = await api.get(
              `/analytics/${endpoint}`
            );

            return {
              name: reportName,
              data: response.data,
              error: null,
            };
          } catch (error) {
            console.error(
              `Failed to load ${reportName} report:`,
              error
            );

            return {
              name: reportName,
              data: null,
              error:
                error.response?.data?.detail ||
                error.message ||
                'Unable to load report.',
            };
          }
        }
      )
    );

    const reportData = {};
    const reportErrors = {};

    results.forEach((result) => {
      reportData[result.name] = result.data;

      if (result.error) {
        reportErrors[result.name] = result.error;
      }
    });

    setReports(reportData);
    setErrors(reportErrors);
    setLastUpdated(new Date());
    setLoading(false);
  }, []);

  useEffect(() => {
    loadReports();
  }, [loadReports]);

  const overview = reports.overview || {};
  const sales = reports.sales || {};
  const inventory = reports.inventory || {};
  const payments = reports.payments || {};
  const returns = reports.returns || {};
  const products = reports.products || {};

  const overviewAvailable = Boolean(reports.overview);

  return (
    <div className="space-y-6 pb-8">
      {/* Page heading */}
      <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">
            Reports & Analytics
          </h1>
          <p className="mt-1 text-sm text-gray-500">
            Monitor sales, inventory, payments and business performance.
          </p>
          {lastUpdated && (
            <p className="mt-2 text-xs text-gray-400">
              Last updated: {lastUpdated.toLocaleTimeString()}
            </p>
          )}
        </div>

        <button
          type="button"
          onClick={loadReports}
          disabled={loading}
          className="inline-flex items-center justify-center gap-2 rounded-lg bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-60"
        >
          <RefreshCw
            size={17}
            className={loading ? 'animate-spin' : ''}
          />
          {loading ? 'Refreshing...' : 'Refresh Reports'}
        </button>
      </div>

      {/* Loading */}
      {loading && Object.keys(reports).length === 0 && (
        <div className="rounded-xl border border-gray-200 bg-white p-10 text-center">
          <RefreshCw
            size={30}
            className="mx-auto animate-spin text-indigo-600"
          />
          <p className="mt-3 text-sm text-gray-500">
            Loading business reports...
          </p>
        </div>
      )}

      {/* API errors */}
      {Object.entries(errors).length > 0 && (
        <div className="rounded-xl border border-amber-200 bg-amber-50 p-4">
          <div className="flex items-start gap-3">
            <AlertTriangle
              size={20}
              className="mt-0.5 shrink-0 text-amber-600"
            />
            <div>
              <h3 className="font-semibold text-amber-900">
                Some reports could not be loaded
              </h3>

              <ul className="mt-2 space-y-1 text-sm text-amber-800">
                {Object.entries(errors).map(([name, message]) => (
                  <li key={name}>
                    <span className="font-semibold capitalize">
                      {name}:
                    </span>{' '}
                    {message}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}

      {/* Overview */}
      {overviewAvailable && (
        <>
          <div>
            <div className="mb-4 flex items-center gap-2">
              <Activity size={20} className="text-indigo-600" />
              <h2 className="text-lg font-bold text-gray-900">
                Business Overview
              </h2>
            </div>

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
              <MetricCard
                title="Total Products"
                value={formatNumber(overview.products?.total)}
                icon={Package}
                color="bg-blue-50 text-blue-600"
              />

              <MetricCard
                title="Total Inventory Units"
                value={formatNumber(overview.inventory?.total_units)}
                icon={Boxes}
                color="bg-purple-50 text-purple-600"
              />

              <MetricCard
                title="Total Orders"
                value={formatNumber(overview.orders?.total)}
                icon={ShoppingCart}
                color="bg-green-50 text-green-600"
              />

              <MetricCard
                title="Delivered Revenue"
                value={formatCurrency(
                  overview.orders?.delivered_revenue
                )}
                icon={TrendingUp}
                color="bg-emerald-50 text-emerald-600"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 gap-5 xl:grid-cols-2">
            <ReportSection
              title="Order Status Overview"
              subtitle="Number of orders in each status"
            >
              <BreakdownList
                data={overview.orders?.by_status}
              />
            </ReportSection>

            <ReportSection
              title="Inventory Overview"
              subtitle="Current stock information"
            >
              <div className="grid grid-cols-2 gap-4">
                <div className="rounded-lg bg-gray-50 p-4">
                  <p className="text-sm text-gray-500">
                    Inventory Products
                  </p>
                  <p className="mt-2 text-xl font-bold text-gray-900">
                    {formatNumber(
                      overview.inventory?.total_products
                    )}
                  </p>
                </div>

                <div className="rounded-lg bg-amber-50 p-4">
                  <p className="text-sm text-amber-700">
                    Low Stock Products
                  </p>
                  <p className="mt-2 text-xl font-bold text-amber-800">
                    {formatNumber(
                      overview.inventory?.low_stock_products
                    )}
                  </p>
                </div>
              </div>
            </ReportSection>
          </div>
        </>
      )}

      {/* Sales */}
      {reports.sales && (
        <>
          <div className="flex items-center gap-2">
            <DollarSign size={21} className="text-green-600" />
            <h2 className="text-lg font-bold text-gray-900">
              Sales Report
            </h2>
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <MetricCard
              title="Total Orders"
              value={formatNumber(sales.total_orders)}
              icon={ShoppingCart}
              color="bg-blue-50 text-blue-600"
            />

            <MetricCard
              title="Completed Sales"
              value={formatNumber(sales.completed_sales_count)}
              icon={TrendingUp}
              color="bg-green-50 text-green-600"
            />

            <MetricCard
              title="Completed Revenue"
              value={formatCurrency(sales.completed_sales_revenue)}
              icon={DollarSign}
              color="bg-emerald-50 text-emerald-600"
            />

            <MetricCard
              title="Average Order Value"
              value={formatCurrency(sales.average_order_value)}
              icon={BarChart3}
              color="bg-purple-50 text-purple-600"
            />
          </div>

          <div className="grid grid-cols-1 gap-5 xl:grid-cols-2">
            <ReportSection
              title="Orders by Status"
              subtitle="Order count grouped by status"
            >
              <BreakdownList data={sales.orders_by_status} />
            </ReportSection>

            <ReportSection
              title="Revenue by Status"
              subtitle="Order value grouped by status"
            >
              <BreakdownList
                data={sales.revenue_by_status}
                currency
              />
            </ReportSection>
          </div>

          <ReportSection
            title="Sales Summary"
            subtitle="Additional sales and order values"
          >
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
              {[
                ['Non-cancelled Orders', formatNumber(sales.non_cancelled_orders)],
                ['Non-cancelled Order Value', formatCurrency(sales.non_cancelled_order_value)],
                ['Discounts Given', formatCurrency(sales.total_discounts)],
                ['Shipping Charges', formatCurrency(sales.total_shipping_charges)],
              ].map(([label, value]) => (
                <div key={label} className="rounded-lg bg-gray-50 p-4">
                  <p className="text-sm text-gray-500">{label}</p>
                  <p className="mt-2 text-lg font-bold text-gray-900">
                    {value}
                  </p>
                </div>
              ))}
            </div>
          </ReportSection>
        </>
      )}

      {/* Inventory */}
      {reports.inventory && (
        <>
          <div className="flex items-center gap-2">
            <Boxes size={21} className="text-purple-600" />
            <h2 className="text-lg font-bold text-gray-900">
              Inventory Report
            </h2>
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <MetricCard
              title="Total Units"
              value={formatNumber(inventory.total_units)}
              icon={Boxes}
              color="bg-blue-50 text-blue-600"
            />

            <MetricCard
              title="Low Stock Products"
              value={formatNumber(inventory.low_stock_products)}
              icon={AlertTriangle}
              color="bg-amber-50 text-amber-600"
            />

            <MetricCard
              title="Out of Stock"
              value={formatNumber(inventory.out_of_stock_products)}
              icon={Package}
              color="bg-red-50 text-red-600"
            />

            <MetricCard
              title="Total Stock Value"
              value={formatCurrency(inventory.total_stock_value)}
              icon={DollarSign}
              color="bg-green-50 text-green-600"
            />
          </div>

          <ReportSection
            title="Product Inventory Details"
            subtitle="Stock quantity and stock value for each product"
          >
            {inventory.products?.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full min-w-[650px] text-left text-sm">
                  <thead className="bg-gray-50 text-xs uppercase text-gray-500">
                    <tr>
                      <th className="px-4 py-3">Product</th>
                      <th className="px-4 py-3">SKU</th>
                      <th className="px-4 py-3">Price</th>
                      <th className="px-4 py-3">Quantity</th>
                      <th className="px-4 py-3">Stock Value</th>
                    </tr>
                  </thead>

                  <tbody className="divide-y divide-gray-100">
                    {inventory.products.map((product) => (
                      <tr key={product.product_id}>
                        <td className="px-4 py-3 font-medium text-gray-900">
                          {product.product_name}
                        </td>
                        <td className="px-4 py-3 text-gray-500">
                          {product.sku}
                        </td>
                        <td className="px-4 py-3">
                          {formatCurrency(product.price)}
                        </td>
                        <td className="px-4 py-3">
                          <span className={`rounded-full px-2 py-1 text-xs font-semibold ${
                            product.quantity === 0
                              ? 'bg-red-100 text-red-700'
                              : product.quantity <= 10
                                ? 'bg-amber-100 text-amber-700'
                                : 'bg-green-100 text-green-700'
                          }`}>
                            {formatNumber(product.quantity)}
                          </span>
                        </td>
                        <td className="px-4 py-3 font-semibold">
                          {formatCurrency(product.stock_value)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <EmptyState message="No inventory product details available." />
            )}
          </ReportSection>
        </>
      )}

      {/* Payments */}
      {reports.payments && (
        <>
          <div className="flex items-center gap-2">
            <CreditCard size={21} className="text-blue-600" />
            <h2 className="text-lg font-bold text-gray-900">
              Payments & Refunds
            </h2>
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <MetricCard
              title="Total Payments"
              value={formatNumber(payments.payments?.total)}
              icon={CreditCard}
              color="bg-blue-50 text-blue-600"
            />

            <MetricCard
              title="Successful Payments"
              value={formatNumber(payments.payments?.successful_count)}
              icon={TrendingUp}
              color="bg-green-50 text-green-600"
            />

            <MetricCard
              title="Successful Payment Amount"
              value={formatCurrency(payments.payments?.successful_amount)}
              icon={DollarSign}
              color="bg-emerald-50 text-emerald-600"
            />

            <MetricCard
              title="Successful Refund Amount"
              value={formatCurrency(payments.refunds?.successful_amount)}
              icon={RotateCcw}
              color="bg-purple-50 text-purple-600"
            />
          </div>

          <div className="grid grid-cols-1 gap-5 xl:grid-cols-2">
            <ReportSection
              title="Payment Status"
              subtitle="Payments grouped by status"
            >
              <BreakdownList data={payments.payments?.by_status} />
            </ReportSection>

            <ReportSection
              title="Refund Status"
              subtitle="Refunds grouped by status"
            >
              <BreakdownList data={payments.refunds?.by_status} />
            </ReportSection>
          </div>
        </>
      )}

      {/* Returns */}
      {reports.returns && (
        <>
          <div className="flex items-center gap-2">
            <RotateCcw size={21} className="text-orange-600" />
            <h2 className="text-lg font-bold text-gray-900">
              Returns Report
            </h2>
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
            <MetricCard
              title="Return Requests"
              value={formatNumber(returns.total_return_requests)}
              icon={RotateCcw}
              color="bg-orange-50 text-orange-600"
            />

            <MetricCard
              title="Returned Quantity"
              value={formatNumber(returns.total_returned_quantity)}
              icon={Package}
              color="bg-blue-50 text-blue-600"
            />

            <MetricCard
              title="Successful Refund Amount"
              value={formatCurrency(returns.successful_refund_amount)}
              icon={DollarSign}
              color="bg-green-50 text-green-600"
            />
          </div>

          <div className="grid grid-cols-1 gap-5 xl:grid-cols-2">
            <ReportSection
              title="Returns by Status"
              subtitle="Return request distribution"
            >
              <BreakdownList data={returns.returns_by_status} />
            </ReportSection>

            <ReportSection
              title="Refunds by Status"
              subtitle="Refund processing distribution"
            >
              <BreakdownList data={returns.refunds_by_status} />
            </ReportSection>
          </div>

          <ReportSection title="Refund Summary">
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div className="rounded-lg bg-gray-50 p-4">
                <p className="text-sm text-gray-500">
                  Total Refund Amount
                </p>
                <p className="mt-2 text-xl font-bold text-gray-900">
                  {formatCurrency(returns.total_refund_amount)}
                </p>
              </div>

              <div className="rounded-lg bg-green-50 p-4">
                <p className="text-sm text-green-700">
                  Successfully Refunded
                </p>
                <p className="mt-2 text-xl font-bold text-green-800">
                  {formatCurrency(returns.successful_refund_amount)}
                </p>
              </div>
            </div>
          </ReportSection>
        </>
      )}

      {/* Product performance */}
      {reports.products && (
        <>
          <div className="flex items-center gap-2">
            <Package size={21} className="text-indigo-600" />
            <h2 className="text-lg font-bold text-gray-900">
              Product Performance
            </h2>
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <MetricCard
              title="Active Products"
              value={formatNumber(products.total_active_products)}
              icon={Package}
              color="bg-green-50 text-green-600"
            />

            <MetricCard
              title="Inactive Products"
              value={formatNumber(products.inactive_products)}
              icon={AlertTriangle}
              color="bg-red-50 text-red-600"
            />

            <MetricCard
              title="Minimum Price"
              value={formatCurrency(products.price_statistics?.minimum_price)}
              icon={DollarSign}
              color="bg-blue-50 text-blue-600"
            />

            <MetricCard
              title="Average Price"
              value={formatCurrency(products.price_statistics?.average_price)}
              icon={BarChart3}
              color="bg-purple-50 text-purple-600"
            />
          </div>

          <div className="grid grid-cols-1 gap-5 xl:grid-cols-2">
            <ReportSection
              title="Products by Category"
              subtitle="Active products grouped by category"
            >
              <BreakdownList data={products.products_by_category} />
            </ReportSection>

            <ReportSection
              title="Products by Brand"
              subtitle="Active products grouped by brand"
            >
              <BreakdownList data={products.products_by_brand} />
            </ReportSection>
          </div>

          <ReportSection
            title="Products Without Inventory"
            subtitle="Active products that do not have an inventory record"
          >
            {products.products_without_inventory?.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full min-w-[450px] text-left text-sm">
                  <thead className="bg-gray-50 text-xs uppercase text-gray-500">
                    <tr>
                      <th className="px-4 py-3">Product ID</th>
                      <th className="px-4 py-3">Product Name</th>
                      <th className="px-4 py-3">SKU</th>
                    </tr>
                  </thead>

                  <tbody className="divide-y divide-gray-100">
                    {products.products_without_inventory.map((product) => (
                      <tr key={product.product_id}>
                        <td className="px-4 py-3">{product.product_id}</td>
                        <td className="px-4 py-3 font-medium">
                          {product.product_name}
                        </td>
                        <td className="px-4 py-3 text-gray-500">
                          {product.sku}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <EmptyState message="All active products have inventory records." />
            )}
          </ReportSection>
        </>
      )}

      {/* No reports loaded */}
      {!loading &&
        Object.values(reports).every((report) => report === null || report === undefined) && (
          <div className="rounded-xl border border-gray-200 bg-white p-8 text-center">
            <BarChart3
              size={36}
              className="mx-auto text-gray-400"
            />
            <h3 className="mt-3 font-semibold text-gray-900">
              Reports are unavailable
            </h3>
            <p className="mt-1 text-sm text-gray-500">
              Check the Analytics Service and API Gateway, then refresh.
            </p>
          </div>
        )}
    </div>
  );
}