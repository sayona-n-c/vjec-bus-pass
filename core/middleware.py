"""
core/middleware.py
──────────────────
NoCacheAuthMiddleware: adds Cache-Control: no-store headers to every
HTTP response served to an authenticated user.

This prevents the browser from caching authenticated pages in its disk
or memory cache. Combined with the bfcache JS guard in base.html, it
ensures that pressing the Back button after logout always triggers a
full server round-trip, causing @login_required to redirect to /login/.
"""


class NoCacheAuthMiddleware:
    """
    For every request where the user is authenticated, attach
    aggressive no-cache headers to the response so the browser
    never serves a stale authenticated page from its cache.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Apply only when a user session is active
        if request.user.is_authenticated:
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate, private'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'

        return response
