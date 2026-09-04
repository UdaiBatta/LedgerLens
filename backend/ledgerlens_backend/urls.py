from django.contrib import admin
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from reconciliation.api_views import FinancialRecordViewSet, OverviewMetricsView, ReconciliationCaseViewSet
from reconciliation.views import SystemHealthView


router = DefaultRouter()
router.register("cases", ReconciliationCaseViewSet, basename="reconciliation-case")
router.register("records", FinancialRecordViewSet, basename="financial-record")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health/", SystemHealthView.as_view(), name="system-health"),
    path("api/metrics/overview/", OverviewMetricsView.as_view(), name="overview-metrics"),
    path("api/", include(router.urls)),
]
