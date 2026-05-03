from django.utils import timezone


class DefaultCurrencyMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not request.session.get('currency'):
            request.session['currency'] = 'QAR'
        return self.get_response(request)
    
# ✅ Track if user is active (online)
class ActiveUserMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            request.user.is_active_now = True  # temp flag (per request)
        return self.get_response(request)


# ✅ Track last activity timestamp
class LastActivityMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            request.session['last_activity'] = str(timezone.now())
        return self.get_response(request)