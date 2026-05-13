# Quick Start: Production Optimization (30 Days)

## Week 1: CRITICAL FIXES (Do This First!)

### Day 1-2: Security & Settings
```bash
# 1. Fix Django settings for production
# File: RevSource_system/settings.py

# BEFORE:
DEBUG = True
ALLOWED_HOSTS = ['*']
SECRET_KEY = 'your-secret-key-here'  # HARDCODED!

# AFTER:
DEBUG = os.getenv('DEBUG', False) == 'True'
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost').split(',')
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY')  # From environment

# 2. Add login protection
# File: RevSource_system/finance/views.py

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin

@login_required
def accounting_grouping(request):
    # ... existing code ...

class AccountListView(LoginRequiredMixin, ListView):
    # ... existing code ...
```

**Time:** 30 minutes  
**Impact:** 🔴 CRITICAL for security

---

### Day 2-3: Input Validation
```python
# File: RevSource_system/finance/forms.py

from django import forms
from django.core.exceptions import ValidationError

class JournalLineFormSet(forms.BaseInlineFormSet):
    def clean(self):
        super().clean()
        
        # Check debit/credit balance
        total_debit = Decimal('0.00')
        total_credit = Decimal('0.00')
        
        for form in self.forms:
            if not form.cleaned_data:
                continue
            total_debit += form.cleaned_data.get('debit', Decimal('0.00'))
            total_credit += form.cleaned_data.get('credit', Decimal('0.00'))
        
        if total_debit != total_credit:
            raise ValidationError(
                f"Journal must be balanced. Debit: {total_debit}, Credit: {total_credit}"
            )

class AccountForm(forms.ModelForm):
    def clean_code(self):
        code = self.cleaned_data['code'].upper()
        # Check for duplicates
        existing = Account.objects.filter(
            code__iexact=code
        ).exclude(pk=self.instance.pk)
        if existing.exists():
            raise ValidationError(f"Account code '{code}' already exists")
        return code
```

**Time:** 1 hour  
**Impact:** 🟠 HIGH for data integrity

---

## Week 2: DATABASE OPTIMIZATION

### Day 4-5: Add Indexes
```python
# File: RevSource_system/finance/models.py

class Account(models.Model):
    code = models.CharField(max_length=20, unique=True, db_index=True)
    name = models.CharField(max_length=100, db_index=True)
    type = models.CharField(max_length=20, choices=ACCOUNT_TYPES, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['type', 'is_active'], name='idx_type_active'),
            models.Index(fields=['is_active', 'code'], name='idx_active_code'),
        ]

class JournalEntry(models.Model):
    date = models.DateField(db_index=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, db_index=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['user', '-date'], name='idx_user_date'),
            models.Index(fields=['date'], name='idx_date'),
        ]

class JournalLine(models.Model):
    journal_entry = models.ForeignKey(
        JournalEntry, on_delete=models.CASCADE, db_index=True
    )
    account = models.ForeignKey(
        Account, on_delete=models.CASCADE, db_index=True
    )
```

**Commands:**
```bash
python manage.py makemigrations finance
python manage.py migrate
```

**Time:** 30 minutes (+ migration time)  
**Impact:** 🔴 CRITICAL for query performance

---

### Day 6-7: Setup Redis Caching
```bash
# 1. Install redis django
pip install django-redis

# 2. Update settings.py

CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'SOCKET_CONNECT_TIMEOUT': 5,
            'SOCKET_TIMEOUT': 5,
        }
    }
}

# 3. Add caching to views

from django.views.decorators.cache import cache_page

@cache_page(60)  # Cache for 60 seconds
@login_required
def accounting_grouping(request):
    # ... existing code ...
```

**Time:** 1 hour  
**Impact:** 🟠 HIGH for performance (3-5x speedup)

---

## Week 3: MONITORING & TESTING

### Day 8-9: Error Logging
```python
# File: RevSource_system/settings.py

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'WARNING',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/var/log/django/finance.log',
            'maxBytes': 1024 * 1024 * 10,  # 10MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'INFO',
    },
}

# File: RevSource_system/finance/views.py
import logging

logger = logging.getLogger(__name__)

def accounting_grouping(request):
    try:
        # ... your code ...
    except Exception as e:
        logger.error(f"Error in accounting_grouping: {e}", exc_info=True)
        raise
```

**Time:** 1 hour  
**Impact:** 🟠 HIGH for debugging in production

---

### Day 10: Load Testing
```bash
# Install locust for load testing
pip install locust

# Create locustfile.py
cat > locustfile.py << 'EOF'
from locust import HttpUser, task, between

class FinanceUser(HttpUser):
    wait_time = between(1, 3)
    
    @task
    def view_account_list(self):
        self.client.get("/finance/accounts/")
    
    @task
    def view_grouping(self):
        self.client.get("/finance/accounts/grouping/")

if __name__ == "__main__":
    # Run: locust -f locustfile.py --host=http://localhost:8000
    pass
EOF

# Run load test with 100 concurrent users
locust -f locustfile.py --host=http://localhost:8000 -u 100 -r 10
```

**Time:** 2 hours  
**Impact:** 🟠 HIGH for knowing your performance limits

---

## Week 4: DEPLOYMENT PREPARATION

### Day 11-12: Static Files & Compression
```bash
# Install compression tools
pip install django-compressor whitenoise

# Update settings.py
MIDDLEWARE = [
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.middleware.gzip.GZipMiddleware',
    # ... other middleware
]

STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Collect static files
python manage.py collectstatic --noinput
```

**Time:** 1 hour  
**Impact:** 🟢 MEDIUM for performance

---

### Day 13: Final Testing
```bash
# Create deployment test checklist
python manage.py test finance --settings=settings.production

# Check settings
python manage.py check --deploy

# Run security checks
python manage.py check --security
```

**Time:** 1-2 hours  
**Impact:** 🟢 MEDIUM for confidence

---

### Day 14: Documentation & Deployment
Create these files:
- `DEPLOYMENT.md` - How to deploy to GCP
- `MONITOR.md` - How to monitor in production
- `INCIDENT.md` - Incident response procedures
- `BACKUP.md` - Backup/restore procedures

**Time:** 2-3 hours  
**Impact:** 🟢 MEDIUM for runbook

---

## GCP DEPLOYMENT SETUP (Parallel with above)

### Prerequisites (Do Once)
```bash
# 1. Create GCP project
gcloud projects create finance-app-production

# 2. Create Cloud SQL database
gcloud sql instances create finance-db-prod \
  --database-version=POSTGRES_14 \
  --tier=db-f1-micro \
  --region=us-central1 \
  --backup

# 3. Create database user
gcloud sql users create django_user \
  --instance=finance-db-prod \
  --password=SECURE_PASSWORD_HERE

# 4. Create Redis cache
gcloud redis instances create finance-cache-prod \
  --size=1 \
  --region=us-central1

# 5. Create Cloud Storage bucket for static files
gsutil mb gs://finance-app-static/
```

### Environment Variables for Production
```bash
# Create .env.production file (NEVER commit this!)
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
SECRET_KEY=generate_secure_random_key_here
DATABASE_URL=postgresql://django_user:password@cloud-sql-ip:5432/finance
REDIS_URL=redis://cache-ip:6379/1
GCP_PROJECT_ID=your-project-id
ENVIRONMENT=production
```

---

## ROLLBACK PLAN (If something breaks)

```bash
# Quick rollback to previous version
git revert HEAD~1
python manage.py migrate --no-input
python manage.py collectstatic --noinput
SystemCTL restart gunicorn

# If database corrupted
gcloud sql backups restore BACKUP_ID \
  --backup-instance=finance-db-prod
```

---

## SUCCESS CRITERIA

After 30 days, you should have:

✅ All critical security fixes applied  
✅ Database indexes created  
✅ Redis caching operational  
✅ Error logging configured  
✅ Load test completed (100+ users)  
✅ Backup/restore tested  
✅ Monitoring alerts setup  
✅ Team trained on deployment  
✅ Incident response procedures documented  
✅ **Ready for 500 concurrent users**

---

## DAILY STANDUP TEMPLATE

```
MON:  [  ] Security fixes (30 min)
      [  ] Input validation (1 hr)
      [  ] Code review

TUE:  [  ] Database indexes (30 min)
      [  ] Test migrations (30 min)
      [  ] Code review

WED:  [  ] Redis setup (1 hr)
      [  ] Cache configuration (30 min)
      [  ] Code review

THU:  [  ] Error logging (1 hr)
      [  ] Load testing (1-2 hrs)
      [  ] Analysis

FRI:  [  ] Static files & compression (1 hr)
      [  ] Final testing (1-2 hrs)
      [  ] Deploy to staging
```

---

## EMERGENCY CONTACTS

- **On-Call:** Set up PagerDuty for alerts
- **Escalation:** Define escalation path
- **War Room:** Set up Slack channel for incidents
- **Comms:** Who notifies users on outages?

---

**Total Time Estimate:** 30-40 hours over 2-3 weeks  
**Team Size:** 1-2 developers  
**Ready for Production:** ✅ Yes (after all checks pass)

**Questions?** Review [PRODUCTION_READINESS_REPORT.md](./PRODUCTION_READINESS_REPORT.md)  
**Next Steps:** Start with Week 1 Day 1!
