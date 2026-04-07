from rest_framework.permissions import BasePermission

class IsAuthenticatedAndOwner(BasePermission):
    def has_permission(self, request, view):
        if view.action == 'list':
            return request.user.is_staff
        return request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        return obj == request.user or request.user.is_staff

class IsAuthenticatedOrReadOnly(BasePermission):
    def has_permission(self, request, view):
        if request.method in ['GET', 'HEAD', 'OPTIONS']:
            return True
        return request.user.is_authenticated