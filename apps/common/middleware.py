# apps/common/middleware.py
import threading

_local = threading.local()


def get_current_user():
    """Return the authenticated user for the current request, or None."""
    return getattr(_local, "user", None)


class CurrentUserMiddleware:
    """Stores the authenticated user in thread-local storage for access in signals."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        _local.user = request.user if request.user.is_authenticated else None
        response = self.get_response(request)
        _local.user = None  # clean up after request
        return response