# Production Optimization Guide for Revolving Finance System

**Target:** Medium load (50-500 concurrent users), GCP, 10K+ transactions

---

## 1. CACHING STRATEGY (Priority: CRITICAL)

### 1.1 Exchange Rates Caching
Exchange rates rarely change, but are queried frequently. Implement aggressive caching:

```python
# finance/utils/currency.py
from django.core.cache import cache
from decimal import Decimal

def get_exchange_rate_for_conversion(from_currency, to_currency):
    """Get exchange rate with caching."""
    cache_key = f"exchange_rate_{from_currency.code}_{to_currency.code}"
    
    # Try cache first (1 hour TTL)
    rate = cache.get(cache_key)
    if rate:
        return Decimal(rate)
    
    # Get from DB and cache
    if from_currency == to_currency:
        rate = Decimal('1.0')
    else:
        # Your existing logic
        rate = from_currency.get_rate_to(to_currency)
    
    cache.set(cache_key, str(rate), 3600)  # Cache for 1 hour
    return rate
```

### 1.2 Active Currencies List Caching
```python
# finance/models.py
@classmethod
def get_active_currencies(cls):
    cache_key = 'all_active_currencies'
    currencies = cache.get(cache_key)
    
    if currencies is None:
        currencies = list(cls.objects.filter(is_active=True))
        cache.set(cache_key, currencies, 3600)  # 1 hour
    
    return currencies
```

Invalidate this cache when currencies change:
```python
# In Currency model save()
def save(self, *args, **kwargs):
    super().save(*args, **kwargs)
    cache.delete('all_active_currencies')  # Invalidate
```

### 1.3 Account Totals Caching (Per User Session)
Account totals are recalculated every view load. Cache them in user session:

```python
# finance/views.py
def get_account_totals(request, currency):
    cache_key = f"account_totals_{request.user.id}_{currency.code}"
    totals = cache.get(cache_key)
    
    if totals is None:
        totals = {
            'assets': Account.objects.filter(type='asset').aggregate(Sum('balance'))['total'],
            'liabilities': Account.objects.filter(type='liability').aggregate(Sum('balance'))['total'],
            # ... other totals
        }
        cache.set(cache_key, totals, 300)  # 5 min cache
    
    return totals
```

**GCP Implementation:** Use Cloud Memorystore (Redis)
- Go to Cloud Memorystore in GCP Console
- Create Redis instance (1GB for initial load)
- In Django settings:
```python
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://YOUR_REDIS_IP:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}
```

---

## 2. DATABASE OPTIMIZATION (Priority: HIGH)

### 2.1 Add Database Indexes

```python
# finance/models.py
class Account(models.Model):
    code = models.CharField(max_length=20, unique=True, db_index=True)
    name = models.CharField(max_length=100, db_index=True)
    type = models.CharField(max_length=20, choices=ACCOUNT_TYPES, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['type', 'is_active']),  # For grouping queries
            models.Index(fields=['is_active', 'code']),  # For listing
        ]

class JournalEntry(models.Model):
    date = models.DateField(db_index=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, db_index=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['user', '-date']),  # Common filter pattern
        ]

class JournalLine(models.Model):
    journal_entry = models.ForeignKey(JournalEntry, on_delete=models.CASCADE, db_index=True)
    account = models.ForeignKey(Account, on_delete=models.CASCADE, db_index=True)
```

### 2.2 Query Optimization - Use select_related() and prefetch_related()

```python
# finance/views.py - Account Grouping
def accounting_grouping(request):
    # BEFORE (inefficient)
    accounts = Account.objects.filter(is_active=True).order_by('code')
    
    # AFTER (optimized)
    accounts = Account.objects.filter(
        is_active=True
    ).select_related('type').order_by('code')
    
    # Similar for journal entries
    entries = JournalEntry.objects.filter(
        user=request.user
    ).prefetch_related('journalline_set__account')  # Get lines + accounts in 2 queries
```

### 2.3 Pagination on Large Lists

Already implemented in account_list (paginate_by=25), but verify:
```python
# finance/views.py
class AccountListView(ListView):
    paginate_by = 25  # Keep this, good for 50-500 users
    # For 500+ users, reduce to 10-15 per page
```

---

## 3. API/RESPONSE OPTIMIZATION (Priority: MEDIUM)

### 3.1 Reduce Template Render Time

Use `only()` and `defer()` to fetch only needed fields:
```python
# finance/views.py
accounts = Account.objects.only(
    'code', 'name', 'type', 'balance'
).filter(is_active=True)
# Exclude heavy fields like 'description', 'notes'
```

### 3.2 Enable Gzip Compression

Add to settings.py:
```python
MIDDLEWARE = [
    'django.middleware.gzip.GZipMiddleware',  # Add this first
    'django.middleware.common.CommonMiddleware',
    # ... other middleware
]
```

### 3.3 Minify Frontend Static Files

```bash
# Install whitenoise and django-compressor
pip install whitenoise django-compressor
```

Update settings.py:
```python
MIDDLEWARE = [
    'whitenoise.middleware.WhiteNoiseMiddleware',
    # ...
]

STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
```

---

## 4. CONCURRENT USER HANDLING (Priority: MEDIUM)

### 4.1 Database Connection Pooling

Use PgBouncer for PostgreSQL or Cloud SQL Proxy for GCP:
```bash
# If using Cloud SQL on GCP
pip install cloud-sql-python-connector
```

settings.py:
```python
if os.getenv('ENVIRONMENT') == 'production':
    from google.cloud.sql.connector import Connector
    connector = Connector()
    
    def getconn():
        return connector.connect(
            "project:region:instance",
            "pg8000",
            user="postgres",
            password="password",
            db="finance_db"
        )
    
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'OPTIONS': {'creator': getconn},
        }
    }
```

### 4.2 Session Configuration

Reduce session bloat:
```python
# settings.py
SESSION_COOKIE_AGE = 3600  # 1 hour instead of 2 weeks
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = True
```

---

## 5. MONITORING & LOGGING (Priority: HIGH)

### 5.1 Application Performance Monitoring

```python
# settings.py
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'WARNING',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/var/log/django/finance.log',
            'maxBytes': 1024 * 1024 * 10,  # 10MB
            'backupCount': 5,
        },
        'gcp': {
            'class': 'google.cloud.logging.handlers.CloudLoggingHandler',
        }
    },
    'root': {
        'handlers': ['file', 'gcp'],
        'level': 'INFO',
    },
}
```

### 5.2 Slow Query Detection

```python
# settings.py
if DEBUG:
    LOGGING['loggers'] = {
        'django.db.backends': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
    }
```

### 5.3 GCP Monitoring Setup

```python
# settings.py
INSTALLED_APPS = [
    # ...
    'google.cloud.logging',
]
```

---

## 6. LOAD BALANCING & AUTO-SCALING (GCP) (Priority: MEDIUM)

### 6.1 Cloud Run Deployment (Recommended)

```yaml
# cloudbuild.yaml
steps:
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'gcr.io/$PROJECT_ID/finance-app', '.']
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'gcr.io/$PROJECT_ID/finance-app']
  - name: 'gcr.io/cloud-builders/gke-deploy'
    args: ['run', '--filename=k8s/', '--image=gcr.io/$PROJECT_ID/finance-app', '--location=us-central1']
```

### 6.2 Auto-scaling Configuration

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: finance-app
spec:
  replicas: 3  # Start with 3 instances
  template:
    spec:
      containers:
      - name: finance-app
        resources:
          requests:
            memory: "256Mi"
            cpu: "100m"
          limits:
            memory: "512Mi"
            cpu: "500m"

---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: finance-app-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: finance-app
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

---

## 7. SECURITY FOR PRODUCTION (Priority: CRITICAL)

### 7.1 Essential Settings

```python
# settings.py
DEBUG = False
ALLOWED_HOSTS = ['yourdomain.com', 'www.yourdomain.com']
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY')  # Use environment variable

# HTTPS only
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Database
DATABASES['default']['CONN_MAX_AGE'] = 600  # Connection pooling
```

### 7.2 Input Validation & Rate Limiting

```python
# finance/views.py
from django.views.decorators.cache import cache_page
from django.views.decorators.http import require_http_methods

@require_http_methods(["GET", "POST"])
@cache_page(60)  # Cache for 1 minute
def accounting_grouping(request):
    # ...
```

---

## 8. PERFORMANCE TARGETS

| Metric | Target | Current |
|--------|--------|---------|
| Page Load Time | < 200ms | ? |
| Database Query Time | < 50ms | ? |
| Currency Conversion | < 5ms | ? |
| Account Grouping | < 100ms | ? |
| Concurrent Users | 50-500 | ? |
| Cache Hit Rate | > 80% | ? |

---

## 9. DEPLOYMENT CHECKLIST

- [ ] Run `python manage.py test finance/tests/test_production_ready.py` (all tests pass)
- [ ] Run `python manage.py collectstatic` (static files compiled)
- [ ] Enable Redis cache
- [ ] Add database indexes
- [ ] Configure SSL/HTTPS
- [ ] Set up Cloud Logging on GCP
- [ ] Configure auto-scaling
- [ ] Create database backups strategy
- [ ] Set up monitoring alerts
- [ ] Load test with 100+ concurrent users
- [ ] Set up CI/CD pipeline

---

## 10. NEXT STEPS

1. **This Week:**
   - Implement Redis caching
   - Add database indexes
   - Run production tests

2. **Next Week:**
   - Set up GCP auto-scaling
   - Configure Cloud Logging
   - Load testing

3. **Before Production:**
   - Run full test suite
   - Performance audit
   - Security audit
   - Backup/recovery testing

---

## Quick Commands

```bash
# Run optimization tests
python manage.py test finance.tests.test_production_ready -v 2

# Check query count
python manage.py shell
>>> from django.test.utils import CaptureQueriesContext
>>> with CaptureQueriesContext() as ctx:
...     # run your code
>>> len(ctx.captured_queries)

# Collect static files
python manage.py collectstatic --noinput

# Check for N+1 queries
pip install django-debug-toolbar

# Monitor slow queries
python manage.py runserver --settings=settings.production
```
