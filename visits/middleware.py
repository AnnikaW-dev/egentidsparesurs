# visits/middleware.py — record a public page view after the response is ready

class VisitTrackingMiddleware:
    """Count public page views for the admin traffic overview."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        from .tracking import record_visit

        record_visit(request, response)
        return response
