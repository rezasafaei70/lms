from rest_framework import permissions
from apps.accounts.models import User


class IsSuperAdmin(permissions.BasePermission):
    """
    Permission for super admin only
    """
    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.role == User.UserRole.SUPER_ADMIN
        )


class IsBranchManager(permissions.BasePermission):
    """
    Permission for branch managers
    """
    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.role == User.UserRole.BRANCH_MANAGER
        )


class IsTeacher(permissions.BasePermission):
    """
    Permission for teachers
    """
    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.role == User.UserRole.TEACHER
        )


class IsStudent(permissions.BasePermission):
    """
    Permission for students
    """
    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.role == User.UserRole.STUDENT
        )


class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Permission for object owner or admin
    """
    def has_object_permission(self, request, view, obj):
        # Admin can access everything
        if request.user.role in [
            User.UserRole.SUPER_ADMIN,
            User.UserRole.BRANCH_MANAGER
        ]:
            return True
        
        # Check if user is owner
        if hasattr(obj, 'user'):
            return obj.user == request.user
        elif hasattr(obj, 'student'):
            return obj.student == request.user
        elif hasattr(obj, 'teacher'):
            return obj.teacher == request.user
        
        return False


class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Read-only for everyone, write for admins only
    """
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        
        return (
            request.user and
            request.user.is_authenticated and
            request.user.role in [
                User.UserRole.SUPER_ADMIN,
                User.UserRole.BRANCH_MANAGER
            ]
        )