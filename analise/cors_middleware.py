from django.http import HttpResponse


class CorsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.method == "OPTIONS":
            response = HttpResponse()
            self._adicionar_cors_headers(response)
            return response

        response = self.get_response(request)
        self._adicionar_cors_headers(response)
        return response

    def _adicionar_cors_headers(self, response):
        response["Access-Control-Allow-Origin"] = "*"
        response["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
        response["Access-Control-Allow-Headers"] = (
            "Authorization, Content-Type, X-Requested-With, Accept, Origin, Range"
        )
        response["Access-Control-Expose-Headers"] = "Content-Length, Content-Range"
        response["Access-Control-Max-Age"] = "86400"