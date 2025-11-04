from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from django.db.models import Count, Q

from .models import Branch, Classroom, BranchStaff
from .serializers import (
    BranchSerializer, BranchListSerializer, ClassroomSerializer,
    BranchStaffSerializer
)
from utils.permissions import IsSuperAdmin, IsBranchManager
from utils.pagination import StandardResultsSetPagination


class BranchViewSet(viewsets.ModelViewSet):
    """
    Branch ViewSet
    """
    queryset = Branch.objects.filter(is_deleted=False)
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'city', 'province']
    search_fields = ['name', 'code', 'address', 'city']
    ordering_fields = ['name', 'created_at', 'established_date']

    def get_serializer_class(self):
        if self.action == 'list':
            return BranchListSerializer
        return BranchSerializer

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsSuperAdmin()]
        return [IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        queryset = super().get_queryset()
        
        # Branch managers only see their branches
        if user.role == user.UserRole.BRANCH_MANAGER:
            queryset = queryset.filter(manager=user)
        
        return queryset.annotate(
            classrooms_count=Count('classrooms', filter=Q(classrooms__is_active=True))
        )

    @action(detail=True, methods=['get'], url_path='classrooms')
    def get_classrooms(self, request, pk=None):
        """
        Get all classrooms in a branch
        GET /api/v1/branches/{id}/classrooms/
        """
        branch = self.get_object()
        classrooms = branch.classrooms.filter(is_deleted=False)
        serializer = ClassroomSerializer(classrooms, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'], url_path='staff')
    def get_staff(self, request, pk=None):
        """
        Get all staff in a branch
        GET /api/v1/branches/{id}/staff/
        """
        branch = self.get_object()
        staff = branch.staff.filter(is_active=True)
        serializer = BranchStaffSerializer(staff, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='add-staff')
    def add_staff(self, request, pk=None):
        """
        Add staff to branch
        POST /api/v1/branches/{id}/add-staff/
        {
            "user": "user_id",
            "position": "مدرس"
        }
        """
        branch = self.get_object()
        data = request.data.copy()
        data['branch'] = branch.id
        
        serializer = BranchStaffSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        return Response({
            'message': 'کارمند با موفقیت اضافه شد',
            'staff': serializer.data
        }, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get'], url_path='statistics')
    def statistics(self, request, pk=None):
        """
        Get branch statistics
        GET /api/v1/branches/{id}/statistics/
        """
        branch = self.get_object()
        
        stats = {
            'total_classrooms': branch.classrooms.count(),
            'active_classrooms': branch.classrooms.filter(is_active=True).count(),
            'total_capacity': branch.total_capacity,
            'staff_count': branch.staff.filter(is_active=True).count(),
            # بعداً با enrollments کامل می‌شود
            'current_students': 0,
            'total_classes': 0,
        }
        
        return Response(stats)

    @action(detail=False, methods=['get'], url_path='active')
    def active_branches(self, request):
        """
        Get all active branches
        GET /api/v1/branches/active/
        """
        branches = self.get_queryset().filter(status=Branch.BranchStatus.ACTIVE)
        serializer = self.get_serializer(branches, many=True)
        return Response(serializer.data)


class ClassroomViewSet(viewsets.ModelViewSet):
    """
    Classroom ViewSet
    """
    queryset = Classroom.objects.filter(is_deleted=False)
    serializer_class = ClassroomSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['branch', 'is_active', 'has_projector', 'has_smartboard']
    search_fields = ['name', 'room_number', 'description']
    ordering_fields = ['name', 'room_number', 'capacity']

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsSuperAdmin() or IsBranchManager()]
        return [IsAuthenticated()]

    @action(detail=False, methods=['get'], url_path='available')
    def available_classrooms(self, request):
        """
        Get available classrooms for scheduling
        GET /api/v1/branches/classrooms/available/?branch=id&date=2024-01-01&time=10:00
        """
        branch_id = request.query_params.get('branch')
        date = request.query_params.get('date')
        time = request.query_params.get('time')
        
        classrooms = self.get_queryset().filter(
            is_active=True,
            branch_id=branch_id
        )
        
        # TODO: فیلتر کردن براساس زمان‌بندی کلاس‌ها (بعداً با ماژول courses)
        
        serializer = self.get_serializer(classrooms, many=True)
        return Response(serializer.data)


class BranchStaffViewSet(viewsets.ModelViewSet):
    """
    Branch Staff ViewSet
    """
    queryset = BranchStaff.objects.all()
    serializer_class = BranchStaffSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['branch', 'is_active']
    search_fields = ['user__first_name', 'user__last_name', 'position']
    ordering_fields = ['assigned_date', 'position']

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsSuperAdmin() or IsBranchManager()]
        return [IsAuthenticated()]