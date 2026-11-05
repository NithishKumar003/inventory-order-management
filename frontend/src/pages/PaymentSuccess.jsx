
import { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {
  CheckCircle2,
  Clock,
  AlertCircle,
  Package,
} from 'lucide-react';
import api from '../services/api';

export default function PaymentSuccess() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  const [status, setStatus] = useState('checking');
  const [message, setMessage] = useState(
    'Verifying your payment with Stripe...'
  );

  const orderId = localStorage.getItem('pending_order_id');
  const sessionId = searchParams.get('session_id');

  useEffect(() => {
    let active = true;

    async function verifyPayment() {
      if (!orderId || !sessionId) {
        if (active) {
          setStatus('error');
          setMessage(
            'Order or Stripe session information is missing. Please check your orders.'
          );
        }
        return;
      }

      try {
        const response = await api.post(
          '/payments/verify-session',
          null,
          {
            params: {
              order_id: orderId,
              session_id: sessionId,
            },
          }
        );

        if (!active) return;

        if (response.data.status === 'SUCCESS') {
          setStatus('success');
          setMessage('Your payment has been verified successfully.');
          localStorage.removeItem('pending_payment_id');
          localStorage.removeItem('pending_order_id');
        } else {
          setStatus('pending');
          setMessage(
            'Stripe has not confirmed the payment yet. Please check your order status shortly.'
          );
        }
      } catch (error) {
        console.error('Payment verification failed:', error);

        if (!active) return;

        setStatus('error');
        setMessage(
          error.response?.data?.detail ||
          'We could not verify your payment. Please check your order status.'
        );
      }
    }

    verifyPayment();

    return () => {
      active = false;
    };
  }, [orderId, sessionId]);

  const success = status === 'success';
  const pending = status === 'pending' || status === 'checking';

  return (
    <div className="flex min-h-[70vh] items-center justify-center">
      <div className="w-full max-w-lg rounded-3xl border border-slate-200 bg-white p-8 text-center shadow-sm">
        <div className="mx-auto flex h-20 w-20 items-center justify-center rounded-full bg-slate-100">
          {success ? (
            <CheckCircle2 size={42} className="text-green-600" />
          ) : pending ? (
            <Clock size={42} className="text-blue-600" />
          ) : (
            <AlertCircle size={42} className="text-red-600" />
          )}
        </div>

        <h1 className="mt-6 text-2xl font-extrabold text-slate-900">
          {success
            ? 'Payment Successful!'
            : pending
              ? 'Verifying Payment'
              : 'Payment Verification'}
        </h1>

        <p className="mt-3 text-sm leading-6 text-slate-600">
          {message}
        </p>

        {orderId && (
          <p className="mt-4 text-sm font-semibold text-slate-700">
            Order ID: #{orderId}
          </p>
        )}

        {success && (
          <div className="mt-6 rounded-xl bg-green-50 p-4 text-sm text-green-800">
            Your order payment is confirmed. Thank you for shopping with us!
          </div>
        )}

        <button
          type="button"
          onClick={() =>
            orderId
              ? navigate(`/orders/${orderId}`)
              : navigate('/orders')
          }
          className="mt-7 inline-flex w-full items-center justify-center gap-2 rounded-xl bg-blue-600 px-5 py-3 font-semibold text-white transition hover:bg-blue-700"
        >
          <Package size={18} />
          View My Order
        </button>

        <button
          type="button"
          onClick={() => navigate('/store')}
          className="mt-3 w-full rounded-xl border border-slate-200 px-5 py-3 text-sm font-semibold text-slate-700 hover:bg-slate-50"
        >
          Continue Shopping
        </button>
      </div>
    </div>
  );
}
