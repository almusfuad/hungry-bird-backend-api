from rest_framework import permissions


class IsCustomer(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and \
            (hasattr(request.user, 'role') and int(request.user.role) == 1)
    

class IsRestaurantOwner(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and \
            (hasattr(request.user, 'role') and int(request.user.role) == 2)

class IsDriver(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and \
            (hasattr(request.user, 'role') and int(request.user.role) == 3)