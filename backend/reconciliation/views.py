from django.http import JsonResponse
from django.views import View


class SystemHealthView(View):
    def get(self, request):
        return JsonResponse({"status": "ok", "service": "ledgerlens-backend"})
