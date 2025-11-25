from django.http import HttpResponseBadRequest


class BlockDangerousQueryParamsMiddleware:
    """
    Defense-in-depth guard for CVE-2025-64459-style attacks.

    Blocks any request that includes _connector or _negated in
    query string or POST data.
    """

    DANGEROUS_KEYS = {"_connector", "_negated"}

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Check GET and POST keys (case-sensitive like Django)
        for source_name, params in (("GET", request.GET), ("POST", request.POST)):
            bad = self.DANGEROUS_KEYS.intersection(params.keys())
            if bad:
                # You could also log this server-side if you want
                return HttpResponseBadRequest("Invalid request parameters.")

        return self.get_response(request)
