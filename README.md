# Hungry Bird Backend API

[![Python](https://img.shields.io/badge/Python-3.11-blue?style=flat-square)](https://www.python.org/)
[![Django](https://img.shields.io/badge/Django-5.0-darkgreen?style=flat-square)](https://www.djangoproject.com/)
[![Docker](https://img.shields.io/badge/Docker-Compose-blue?style=flat-square)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)

> A production-ready Django REST API backend for Hungry Bird Food Delivery platform with Docker containerization, Redis caching, Celery task queuing, and WebSocket support.

## Table of Contents

- [Background](#background)
- [Features](#features)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Usage](#usage)
  - [Running with Docker Compose](#running-with-docker-compose)
  - [Environment Configuration](#environment-configuration)
  - [Creating a Superuser](#creating-a-superuser)
  - [Changing Ports](#changing-ports)
- [API Documentation](#api-documentation)
- [Development](#development)
- [Docker Guide](#docker-guide)
- [Contributing](#contributing)
- [Documentation](#documentation)
- [License](#license)

## Background

Hungry Bird is a modern food delivery platform backend API built with Django REST Framework. It handles:

- **User Management** - Authentication, JWT tokens, user profiles with location tracking
- **Restaurant Management** - Restaurant listings, menus, and inventory
- **Order Processing** - Real-time order tracking with WebSocket support
- **Payment Processing** - Stripe integration for secure payments and subscriptions
- **Task Queuing** - Celery with Redis for async task processing
- **Caching** - Redis-based caching and channel layer for WebSockets
- **File Storage** - AWS S3 integration for media files in production
- **API Documentation** - Auto-generated Swagger/OpenAPI docs

## Features

✅ Multi-stage Docker builds with Alpine Linux (optimized image size)  
✅ Docker Compose orchestration for Redis + Django services  
✅ Environment-based configuration management  
✅ Health checks for service dependencies  
✅ Dynamic port configuration  
✅ Django Channels for WebSocket support  
✅ Celery task queue with Redis  
✅ RESTful API with Django REST Framework  
✅ JWT authentication  
✅ Swagger API documentation  
✅ AWS S3 file storage support  
✅ Production-ready with proper signal handling  

## Prerequisites

Before you begin, ensure you have:

- **Docker** (v20.10+) - [Install Docker](https://docs.docker.com/get-docker/)
- **Docker Compose** (v1.29+) - [Install Docker Compose](https://docs.docker.com/compose/install/)
- **Git** - [Install Git](https://git-scm.com/downloads)

*Optional for local development:*
- **Python** 3.11+
- **PostgreSQL** 12+
- **Redis** 7+

## Installation

### Clone the Repository

```bash
git clone https://github.com/wiseX-solutions/hungry-bird-backend-api.git
cd hungry-bird-backend-api
```

### Copy Environment Configuration

```bash
# The .env file contains all necessary configuration
# Update values according to your setup
```

### Build Docker Image

```bash
docker compose build
```

## Usage

### Running with Docker Compose

Start all services (Django API + Redis):

```bash
# Start in foreground (see logs)
docker compose up

# Or start in background (detached mode)
docker compose up -d

# View logs in background mode
docker compose logs -f web
```

Stop all services:

```bash
docker compose down

# Also remove volumes (data will be deleted)
docker compose down --volumes
```

### Environment Configuration

The `.env` file controls the application behavior. Key variables:

```bash
# Django Settings
DEBUG=True                          # Set to False for production
SECRET_KEY=your-secret-key-here     # Change in production
ALLOWED_HOSTS=localhost,127.0.0.1

# Port Configuration
PORT=8000                           # Internal Docker port
EXTERNAL_PORT=8001                  # Port on your host machine

# Redis Configuration
REDIS_HOST=redis                    # Docker service name (do not change)
REDIS_PORT=6379

# Database (Production)
DATABASE_HOST=your-postgres-host
DATABASE_NAME=hungry_bird
DATABASE_USER=postgres
DATABASE_PASSWORD=your-password

# Stripe Payment Gateway
STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_SECRET_KEY=sk_test_...

# AWS S3 (Optional, for production)
AWS_ACCESS_KEY_ID=your-key
AWS_SECRET_ACCESS_KEY=your-secret
AWS_STORAGE_BUCKET_NAME=bucket-name
```

### Creating a Superuser

Access the running Django container and create an admin user:

```bash
# If running in foreground, open another terminal
docker exec -it hungry-bird-api bash

# Inside the container, run:
python manage.py createsuperuser

# You'll be prompted for:
# - Username
# - Email address
# - Password (min 8 characters recommended)
# - Confirm password

# Example:
# Username: admin
# Email: admin@example.com
# Password: YourSecurePassword123!
# Superuser created successfully.

# Exit the container
exit
```

Then access the admin panel at: `http://localhost:8001/admin`

### Changing Ports

To run the API on a different port:

1. **Edit `.env` file:**

```bash
# Change EXTERNAL_PORT to your desired port
EXTERNAL_PORT=9000      # Access API at localhost:9000
PORT=8000               # Keep internal port as is (or change both)
```

2. **Restart services:**

```bash
docker compose down
docker compose up -d
```

3. **Verify the change:**

```bash
docker ps

# Should show: 0.0.0.0:9000->8000/tcp
```

**Examples:**

```bash
# Run on port 3000 (external) → 8000 (internal)
EXTERNAL_PORT=3000
PORT=8000

# Run on port 5000 for both
EXTERNAL_PORT=5000
PORT=5000
```

### Running Management Commands

Execute Django management commands inside the container:

```bash
# Database migrations
docker exec hungry-bird-api python manage.py migrate

# Collect static files
docker exec hungry-bird-api python manage.py collectstatic --noinput

# Run custom seed commands
docker exec hungry-bird-api python manage.py seed_subscription_plans

# Interactive shell
docker exec -it hungry-bird-api python manage.py shell
```

## API Documentation

The API includes auto-generated Swagger documentation:

```
http://localhost:8001/api/docs/
```

(Replace `8001` with your configured `EXTERNAL_PORT`)

**Available Endpoints:**

- `POST /auth/login/` - User login
- `POST /auth/register/` - User registration
- `GET /restaurants/` - List restaurants
- `GET /restaurants/{id}/menu/` - Restaurant menu
- `POST /orders/` - Create order
- `GET /orders/{id}/` - Order details
- `GET /profile/` - User profile
- `POST /reviews/` - Submit review

## Development

### Local Setup (Without Docker)

*For development without Docker:*

```bash
# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Start development server
python manage.py runserver
```

**Note:** You'll need local PostgreSQL and Redis running.

### Useful Commands

```bash
# Check running containers
docker ps

# View container logs
docker logs -f hungry-bird-api

# Access container shell
docker exec -it hungry-bird-api bash

# Remove all containers and volumes
docker compose down --volumes --remove-orphans

# Rebuild without cache
docker compose build --no-cache
```

## Docker Guide

### Understanding the Setup

**Multi-Stage Docker Build:**
- Stage 1: Builder - Compiles Python packages with C extensions
- Stage 2: Runtime - Lightweight production image with only runtime dependencies

**Docker Compose Services:**

1. **redis** - Cache, message broker, channel layer
   - Port: 6379 (configurable via `REDIS_PORT`)
   - Health check: Enabled
   - Volumes: `redis_data`

2. **web** - Django application
   - Port: 8001 → 8000 (configurable)
   - Dependencies: Redis
   - Volumes: Application code, static files, media

### Image Size Optimization

```
Builder stage: ~1.2GB (discarded after build)
Runtime image: ~300-400MB
Final production: ~250MB (with Alpine Linux)
```

### Port Mapping Explanation

```yaml
ports:
  - "${EXTERNAL_PORT:-8001}:${PORT:-8000}"
```

- `EXTERNAL_PORT` - How you access from your host machine
- `PORT` - Internal container port where Django runs
- Default: `localhost:8001` → Container port `8000`

### Troubleshooting

**Issue: Container exits immediately**
```bash
# Check logs
docker compose logs web

# Rebuild image
docker compose build --no-cache
```

**Issue: Port already in use**
```bash
# Change in .env
EXTERNAL_PORT=9000

# Restart
docker compose restart
```

**Issue: Database connection failed**
```bash
# Check DATABASE_HOST in .env
# For external DB, use public IP or hostname, not localhost
DATABASE_HOST=your-postgres-host.rds.amazonaws.com
```

## Contributing

We welcome contributions! Please follow these steps:

1. **Fork the repository**
   ```bash
   git clone https://github.com/YOUR-USERNAME/hungry-bird-backend-api.git
   cd hungry-bird-backend-api
   ```

2. **Create a feature branch**
   ```bash
   git checkout -b feature/amazing-feature
   ```

3. **Make your changes and commit**
   ```bash
   git add .
   git commit -m "Add amazing feature"
   ```

4. **Push to your fork**
   ```bash
   git push origin feature/amazing-feature
   ```

5. **Open a Pull Request**
   - Describe your changes clearly
   - Reference any related issues
   - Ensure tests pass

### Contribution Guidelines

- Follow PEP 8 for Python code
- Write descriptive commit messages
- Add tests for new features
- Update documentation as needed
- Be respectful and constructive

### Code of Conduct

This project adheres to the [Contributor Covenant Code of Conduct](https://www.contributor-covenant.org/).

## Documentation

For comprehensive documentation, including:

- Architecture overview
- API reference
- Database schema
- Deployment guide
- Development workflow
- Troubleshooting guide

**→ [Visit Full Documentation on Notion](https://www.notion.so/your-notion-link-here)**

*Note: Update the Notion link in your actual repository.*

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

**Made with ❤️ by WiseX Solutions**

For support or questions, please open an [issue](https://github.com/wiseX-solutions/hungry-bird-backend-api/issues) or contact us.
