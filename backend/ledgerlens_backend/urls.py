from django.contrib import admin
from django.urls import path

from reconciliation.views import SystemHealthView


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health/", SystemHealthView.as_view(), name="system-health"),
]
