# Inventory and Order Management System

A full-stack Inventory and Order Management System built using **React, FastAPI, Python, SQLite, Docker, and Microservices Architecture**.

The application provides customer shopping functionality and administrative tools for managing products, inventory, orders, payments, returns, reviews, and analytics.

## 1. Project Overview

This project follows a microservices architecture. Each major business function is handled by an independent FastAPI service, with an API Gateway providing a centralized entry point for the frontend.

### Key Features

**Customer Features**
- Customer registration and login with JWT authentication.
- Browse and search products.
- Product categories and product details.
- Shopping cart and wishlist.
- Checkout and online payment integration using Stripe.
- Order history and order tracking.
- Product reviews and ratings.
- Return and refund requests.
- Customer notifications.

**Admin Features**
- Product management.
- Inventory and stock management.
- Low-stock monitoring and threshold configuration.
- Order management and status updates.
- Delivery tracking.
- Return and refund management.
- Customer and review management.
- Analytics and reports.
- Admin notifications.

## 2. Technology Stack

| Layer | Technologies |
|---|---|
| Frontend | React, Vite, JavaScript, Tailwind CSS |
| Backend | Python, FastAPI |
| Database | SQLite |
| Authentication | JWT, Password Hashing, RBAC |
| API Communication | REST APIs, HTTPX |
| API Gateway | FastAPI |
| Messaging | RabbitMQ |
| Caching and Rate Limiting | Redis |
| Payments | Stripe |
| Containerization | Docker, Docker Compose |
| Testing | Pytest |

## 3. System Architecture

The React frontend communicates with the API Gateway. The gateway routes requests to the appropriate backend microservice.

### Microservices

| Service | Port | Responsibility |
|---|---:|---|
| API Gateway | 8000 | Central API entry point and routing |
| Auth Service | 8001 | Authentication and authorization |
| Product Service | 8002 | Product management |
| Inventory Service | 8003 | Stock and inventory management |
| Cart Service | 8004 | Shopping cart and wishlist |
| Order Service | 8005 | Orders and coupons |
| Payment Service | 8006 | Payments and refunds |
| Notification Service | 8007 | Customer and admin notifications |
| Review Service | 8008 | Product reviews and ratings |
| Return Service | 8009 | Returns and refund requests |
| Analytics Service | 8010 | Reports and analytics |

### Additional Infrastructure

- **RabbitMQ:** Message broker for asynchronous communication.
- **Redis:** Caching and rate limiting.
- **Notification Worker:** Background notification processing.
- **React Frontend:** User interface running on port 5173.

## 4. Project Structure

```text
inventory_order_management/
│
├── analytics-service/
├── api-gateway/
├── auth-service/
├── cart-service/
├── inventory-service/
├── notification-service/
├── order-service/
├── payment-service/
├── product-service/
├── return-service/
├── review-service/
│
├── frontend/
├── infrastructure/
├── docs/
├── postman/
│
├── .env.example
├── docker-compose.yml
├── .gitignore
└── README.md
```

Each backend service contains its own application code, dependencies, configuration, and tests.

## 5. Prerequisites

Install the following before running the project:

- Git
- Docker Desktop
- Docker Compose
- Node.js and npm (for local frontend development)
- Python 3.12 or later (for local backend development)

## 6. Installation and Setup

### Step 1: Clone the Repository

```bash
git clone https://github.com/NithishKumar003/inventory-order-management.git

cd inventory-order-management
```

### Step 2: Configure Environment Variables

For security, actual `.env` files are excluded from Git.

Example environment files (`.env.example`) are provided for configuration.

On Windows PowerShell, run these commands from the project root:

```powershell
Copy-Item .env.example .env
Copy-Item auth-service/.env.example auth-service/.env
Copy-Item inventory-service/.env.example inventory-service/.env
Copy-Item cart-service/.env.example cart-service/.env
Copy-Item notification-service/.env.example notification-service/.env
Copy-Item order-service/.env.example order-service/.env
Copy-Item payment-service/.env.example payment-service/.env
Copy-Item return-service/.env.example return-service/.env
Copy-Item review-service/.env.example review-service/.env
Copy-Item analytics-service/.env.example analytics-service/.env
Copy-Item api-gateway/.env.example api-gateway/.env
```

After copying, configure the environment variables before starting the application.

**Important configuration requirements:**

- Replace the placeholder JWT secret with a strong random secret. Keep it consistent across services that verify the same JWTs.
- Replace the internal service token placeholder with a strong shared token across services that use internal authentication.
- Configure matching RabbitMQ credentials in the root and notification service environment files.
- Configure Stripe test credentials for payment checkout and webhook testing.
- Configure service URLs according to the Docker Compose service names.

Never commit real passwords, JWT secrets, Stripe keys, or other credentials to GitHub.

### Step 3: Build and Start the Application

Run the following command from the project root:

```bash
docker compose up --build -d
```

Check container status:

```bash
docker compose ps
```

View application logs:

```bash
docker compose logs -f
```

### Step 4: Access the Application

| Component | URL |
|---|---|
| Frontend | http://localhost:5173 |
| API Gateway | http://localhost:8000 |
| Gateway Swagger UI | http://localhost:8000/docs |
| Gateway ReDoc | http://localhost:8000/redoc |
| RabbitMQ Management | http://localhost:15672 |

Individual backend services expose their FastAPI documentation on their respective ports, where enabled.

Examples:

- Auth: http://localhost:8001/docs
- Products: http://localhost:8002/docs
- Inventory: http://localhost:8003/docs
- Orders: http://localhost:8005/docs
- Payments: http://localhost:8006/docs

### Step 5: Stop the Application

Stop containers:

```bash
docker compose down
```

To remove Docker-managed persistent volumes as well:

```bash
docker compose down -v
```

**Warning:** Removing volumes deletes persisted RabbitMQ and Redis data.

## 7. Running the Frontend Separately

Navigate to the frontend directory:

```bash
cd frontend
```

Install dependencies:

```bash
npm install
```

Start the development server:

```bash
npm run dev
```

Create a production build:

```bash
npm run build
```

## 8. Testing

The backend services use Pytest.

Run tests from an individual service directory:

```bash
python -m pytest -q tests
```

### Backend Test Results

The following results were verified during project submission preparation:

| Service | Tests Passed |
|---|---:|
| Auth Service | 25 |
| API Gateway | 76 |
| Inventory Service | 42 |
| Cart Service | 5 |
| Product Service | 37 |
| Order Service | 54 |
| Payment Service | 60 |
| Notification Service | 11 |
| Return Service | 24 |
| Review Service | 11 |
| Analytics Service | 13 |
| **Total** | **358** |

**All 358 backend tests passed** in the verified test run.

The frontend production build was also verified successfully using:

```bash
npm run build
```

## 9. Security

The application implements the following security measures:

- JWT-based authentication.
- Role-based access control.
- Password hashing.
- Internal service authentication.
- Environment-based secret configuration.
- Sensitive environment files excluded through `.gitignore`.

## 10. GitHub Repository

**Repository:**
https://github.com/NithishKumar003/inventory-order-management

---

## Project Information

| Item | Details |
|---|---|
| Project | Inventory and Order Management System |
| Architecture | Microservices |
| Backend | FastAPI and Python |
| Frontend | React |
| Database | SQLite |
| Messaging | RabbitMQ |
| Caching | Redis |
| Payment Integration | Stripe |
| Deployment | Docker Compose |
