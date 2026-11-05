
import { useNavigate } from 'react-router-dom';
import { AlertCircle, ShoppingCart } from 'lucide-react';

export default function PaymentCancel() {
  const navigate = useNavigate();

  return (
    <div className="flex min-h-[70vh] items-center justify-center">
      <div className="w-full max-w-lg rounded-3xl border border-slate-200 bg-white p-8 text-center shadow-sm">
        <div className="mx-auto flex h-20 w-20 items-center justify-center rounded-full bg-amber-100">
          <AlertCircle size={42} className="text-amber-600" />
        </div>

        <h1 className="mt-6 text-2xl font-extrabold text-slate-900">
          Payment Cancelled
        </h1>

        <p className="mt-3 text-sm leading-6 text-slate-600">
          Your Stripe Checkout session was cancelled or closed.
          Please check your order status before trying again.
        </p>

        <button
          type="button"
          onClick={() => navigate('/orders')}
          className="mt-7 w-full rounded-xl bg-blue-600 px-5 py-3 font-semibold text-white hover:bg-blue-700"
        >
          View My Orders
        </button>

        <button
          type="button"
          onClick={() => navigate('/store')}
          className="mt-3 inline-flex w-full items-center justify-center gap-2 rounded-xl border border-slate-200 px-5 py-3 text-sm font-semibold text-slate-700 hover:bg-slate-50"
        >
          <ShoppingCart size={18} />
          Return to Store
        </button>
      </div>
    </div>
  );
}
