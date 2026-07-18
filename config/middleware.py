"""HTTP performance helpers: cache headers for static/media assets."""

from django.conf import settings


class AssetCacheMiddleware:
    """Set long cache lifetimes for static and media files (Lighthouse cache audit).

    Adjust: change max-age if you need assets to refresh sooner after deploys.
    With hashed/fingerprinted names prefer immutable; here media is content-hashed by upload name.
    """

    # One year in seconds
    MAX_AGE = 60 * 60 * 24 * 365

    def __init__(self, get_response):
        self.get_response = get_response
        self.static_prefix = settings.STATIC_URL
        self.media_prefix = settings.MEDIA_URL

    def __call__(self, request):
        response = self.get_response(request)
        path = request.path
        if path.startswith(self.static_prefix) or path.startswith(self.media_prefix):
            if response.status_code == 200:
                response["Cache-Control"] = f"public, max-age={self.MAX_AGE}, immutable"
        return response
