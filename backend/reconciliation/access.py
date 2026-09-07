from django.conf import settings
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.permissions import BasePermission, SAFE_METHODS

from .models import Organization, OrganizationMembership


def demo_request(request):
    return (settings.DEBUG and settings.LEDGERLENS_DEMO_MODE
            and request.META.get("REMOTE_ADDR") in {"127.0.0.1", "::1"}
            and not request.user.is_authenticated)


class OrganizationAccess(BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated and not demo_request(request):
            return False
        slug = request.META.get("HTTP_X_ORGANIZATION_SLUG", "").strip()
        if not slug:
            raise ValidationError("The X-Organization-Slug header selects your organization.")
        if demo_request(request):
            if slug != "ledgerlens-demo":
                raise PermissionDenied("Demo mode is restricted to ledgerlens-demo.")
            request.organization = Organization.objects.filter(slug=slug).first()
            request.membership = None
            if not request.organization:
                raise NotFound("Seed the demonstration organization first.")
            if request.method not in SAFE_METHODS and getattr(view, "action", "") not in {"ask", "assign"}:
                raise PermissionDenied("Demo mode does not permit ingestion or control changes.")
            return True
        membership = OrganizationMembership.objects.select_related("organization").filter(
            user=request.user, organization__slug=slug).first()
        if not membership:
            raise PermissionDenied("No membership grants access to this organization.")
        if request.method not in SAFE_METHODS and membership.role not in {"analyst", "manager", "administrator"}:
            raise PermissionDenied("This membership is read-only.")
        request.organization = membership.organization
        request.membership = membership
        return True


def require_organization(request):
    return request.organization
