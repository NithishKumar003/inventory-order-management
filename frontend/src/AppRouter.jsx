import { Navigate, Route, Routes } from 'react-router-dom';
import { useEffect, useState } from 'react';

import api from './services/api';

import App from './App';
import Register from './pages/Register';
import Login from './pages/Login';
import Products from './pages/Products';
import Inventory from './pages/Inventory';
import Orders from './pages/Orders';
import Customers from './pages/Customers';
import Cart from './pages/Cart';
import Store from './pages/Store';
import Wishlist from './pages/Wishlist';
import OrderDetails from './pages/OrderDetails';
import Deliveries from './pages/Deliveries';
import Returns from './pages/Returns';
import Reports from './pages/Reports';
import PaymentSuccess from './pages/PaymentSuccess';
import PaymentCancel from './pages/PaymentCancel';
import Notifications from './pages/Notifications';
import Layout from './components/Layout';
import CustomerLayout from './components/CustomerLayout';

export default function AppRouter() {
  const [token, setToken] = useState(
    () => localStorage.getItem('access_token')
  );

  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchCurrentUser() {
      if (!token) {
        setUser(null);
        setLoading(false);
        return;
      }

      try {
        const response = await api.get('/auth/me');
        setUser(response.data);
      } catch (error) {
        console.error('Failed to fetch user:', error);

        localStorage.removeItem('access_token');
        setToken(null);
        setUser(null);
      } finally {
        setLoading(false);
      }
    }

    fetchCurrentUser();
  }, [token]);

  function handleLoginSuccess(accessToken) {
    localStorage.setItem('access_token', accessToken);
    setLoading(true);
    setToken(accessToken);
  }

  function handleLogout() {
    localStorage.removeItem('access_token');
    setToken(null);
    setUser(null);
  }

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-gray-600">Loading your dashboard...</p>
      </div>
    );
  }

  return (
    <Routes>
      <Route
        path="/login"
        element={
          token && user ? (
            <Navigate
              to={user.role === 'admin' ? '/' : '/store'}
              replace
            />
          ) : (
            <Login onLoginSuccess={handleLoginSuccess} />
          )
        }
      />

      <Route
        path="/register"
        element={
          token && user ? (
            <Navigate
              to={user.role === 'admin' ? '/' : '/store'}
              replace
            />
          ) : (
            <Register />
          )
        }
      />

      {token && user?.role === 'admin' && (
        <Route element={<Layout onLogout={handleLogout} />}>
          <Route path="/" element={<App />} />
          <Route path="/products" element={<Products />} />
          <Route path="/inventory" element={<Inventory />} />
          <Route path="/orders" element={<Orders isAdmin />} />
          <Route path="/customers" element={<Customers />} />
          <Route path="/deliveries" element={<Deliveries />} />
          <Route path="/returns" element={<Returns />} />
          <Route path="/reports" element={<Reports />} />
          <Route path="/notifications" element={<Notifications />} />
        </Route>
      )}

      {token && user?.role === 'customer' && (
        <Route element={<CustomerLayout onLogout={handleLogout} />}>
          <Route path="/store" element={<Store />} />
          <Route path="/cart" element={<Cart />} />
          <Route path="/wishlist" element={<Wishlist />} />
          <Route path="/orders" element={<Orders />} />
          <Route path="/orders/:orderId" element={<OrderDetails />} />
          <Route path="/notifications" element={<Notifications />} />

          <Route path="/payment/success" element={<PaymentSuccess />} />
          <Route path="/payment/cancel" element={<PaymentCancel />} />
        </Route>
      )}

      <Route
        path="*"
        element={
          token && user ? (
            <Navigate
              to={user.role === 'admin' ? '/' : '/store'}
              replace
            />
          ) : (
            <Navigate to="/login" replace />
          )
        }
      />
    </Routes>
  );
}