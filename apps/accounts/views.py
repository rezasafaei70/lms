from rest_framework import viewsets, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils import timezone
from django.db.models import Q
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters

from .models import User, StudentProfile, TeacherProfile, OTP, LoginHistory
from .serializers import (
    UserSerializer, StudentProfileSerializer, TeacherProfileSerializer,
    RegisterSerializer, SendOTPSerializer, VerifyOTPSerializer,
    LoginSerializer, PasswordLoginSerializer, ChangePasswordSerializer,
    LoginHistorySerializer
)
from utils.permissions import IsSuperAdmin, IsOwnerOrAdmin, IsTeacher, IsStudent
from utils.pagination import StandardResultsSetPagination


class AuthViewSet(viewsets.GenericViewSet):
    """
    Authentication ViewSet
    """
    permission_classes = [AllowAny]
    serializer_class = SendOTPSerializer

    @action(detail=False, methods=['post'], url_path='send-otp')
    def send_otp(self, request):
        """
        Send OTP to mobile number
        POST /api/v1/accounts/auth/send-otp/
        {
            "mobile": "09123456789",
            "purpose": "login"
        }
        """
        serializer = SendOTPSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        otp = serializer.save()
        
        return Response({
            'message': 'کد تایید با موفقیت ارسال شد',
            'mobile': otp.mobile,
            'expires_in': 120,  # seconds
            # در محیط توسعه می‌توانید کد را برگردانید
            # 'code': otp.code if settings.DEBUG else None
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], url_path='verify-otp')
    def verify_otp(self, request):
        """
        Verify OTP code
        POST /api/v1/accounts/auth/verify-otp/
        {
            "mobile": "09123456789",
            "code": "123456"
        }
        """
        serializer = VerifyOTPSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        return Response({
            'message': 'کد تایید با موفقیت تایید شد',
            'user_exists': not user.first_name == '',
            'user_id': str(user.id),
            'mobile': user.mobile
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], url_path='register')
    def register(self, request):
        """
        Register new user
        POST /api/v1/accounts/auth/register/
        {
            "mobile": "09123456789",
            "first_name": "علی",
            "last_name": "احمدی",
            "email": "ali@example.com",
            "role": "student"
        }
        """
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        # Generate tokens
        refresh = RefreshToken.for_user(user)
        
        # Log login
        self._create_login_history(request, user, True)
        
        return Response({
            'message': 'ثبت نام با موفقیت انجام شد',
            'user': UserSerializer(user).data,
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }
        }, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'], url_path='login')
    def login(self, request):
        """
        Login with OTP
        POST /api/v1/accounts/auth/login/
        {
            "mobile": "09123456789",
            "code": "123456"
        }
        """
        serializer = LoginSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        
        if not user.first_name:
            return Response({
                'error': 'لطفاً ابتدا ثبت نام کنید',
                'requires_registration': True
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Generate tokens
        refresh = RefreshToken.for_user(user)
        
        # Update last login
        user.last_login = timezone.now()
        user.last_login_ip = request.META.get('REMOTE_ADDR')
        user.save()
        
        # Log login
        self._create_login_history(request, user, True)
        
        return Response({
            'message': 'ورود با موفقیت انجام شد',
            'user': UserSerializer(user).data,
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], url_path='login-password')
    def login_password(self, request):
        """
        Login with mobile and password (optional)
        POST /api/v1/accounts/auth/login-password/
        {
            "mobile": "09123456789",
            "password": "password123"
        }
        """
        serializer = PasswordLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        
        # Generate tokens
        refresh = RefreshToken.for_user(user)
        
        # Update last login
        user.last_login = timezone.now()
        user.last_login_ip = request.META.get('REMOTE_ADDR')
        user.save()
        
        # Log login
        self._create_login_history(request, user, True)
        
        return Response({
            'message': 'ورود با موفقیت انجام شد',
            'user': UserSerializer(user).data,
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], url_path='logout', permission_classes=[IsAuthenticated])
    def logout(self, request):
        """
        Logout user (blacklist refresh token)
        POST /api/v1/accounts/auth/logout/
        {
            "refresh": "refresh_token_here"
        }
        """
        try:
            refresh_token = request.data.get('refresh')
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
            
            # Update logout time in login history
            login_history = LoginHistory.objects.filter(
                user=request.user,
                logout_at__isnull=True
            ).order_by('-created_at').first()
            
            if login_history:
                login_history.logout_at = timezone.now()
                login_history.save()
            
            return Response({
                'message': 'خروج با موفقیت انجام شد'
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({
                'error': 'خطا در خروج از سیستم'
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], url_path='refresh-token', permission_classes=[AllowAny])
    def refresh_token(self, request):
        """
        Refresh access token
        POST /api/v1/accounts/auth/refresh-token/
        {
            "refresh": "refresh_token_here"
        }
        """
        try:
            refresh = RefreshToken(request.data.get('refresh'))
            return Response({
                'access': str(refresh.access_token)
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({
                'error': 'توکن نامعتبر است'
            }, status=status.HTTP_401_UNAUTHORIZED)

    def _create_login_history(self, request, user, successful):
        """Helper to create login history"""
        try:
            from user_agents import parse
            user_agent_string = request.META.get('HTTP_USER_AGENT', '')
            user_agent = parse(user_agent_string)
            
            LoginHistory.objects.create(
                user=user,
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=user_agent_string,
                device_type=user_agent.device.family,
                browser=user_agent.browser.family,
                os=user_agent.os.family,
                login_successful=successful
            )
        except Exception as e:
            pass  # Don't fail login if history creation fails


class UserViewSet(viewsets.ModelViewSet):
    """
    User ViewSet
    """
    queryset = User.objects.filter(is_deleted=False)
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['role', 'is_active', 'is_verified', 'gender']
    search_fields = ['first_name', 'last_name', 'mobile', 'email', 'national_code']
    ordering_fields = ['created_at', 'first_name', 'last_name']

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [IsAuthenticated()]
        elif self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsSuperAdmin()]
        return super().get_permissions()

    @action(detail=False, methods=['get'], url_path='me')
    def me(self, request):
        """
        Get current user profile
        GET /api/v1/accounts/users/me/
        """
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)

    @action(detail=False, methods=['put', 'patch'], url_path='update-profile')
    def update_profile(self, request):
        """
        Update current user profile
        PUT/PATCH /api/v1/accounts/users/update-profile/
        """
        serializer = self.get_serializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({
            'message': 'پروفایل با موفقیت بروزرسانی شد',
            'user': serializer.data
        })

    @action(detail=False, methods=['post'], url_path='change-password')
    def change_password(self, request):
        """
        Change user password
        POST /api/v1/accounts/users/change-password/
        {
            "old_password": "old_pass",
            "new_password": "new_pass",
            "new_password_confirm": "new_pass"
        }
        """
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({
            'message': 'رمز عبور با موفقیت تغییر کرد'
        })

    @action(detail=True, methods=['post'], url_path='activate')
    def activate(self, request, pk=None):
        """
        Activate user account (Admin only)
        POST /api/v1/accounts/users/{id}/activate/
        """
        user = self.get_object()
        user.is_active = True
        user.save()
        return Response({
            'message': 'حساب کاربری فعال شد'
        })

    @action(detail=True, methods=['post'], url_path='deactivate')
    def deactivate(self, request, pk=None):
        """
        Deactivate user account (Admin only)
        POST /api/v1/accounts/users/{id}/deactivate/
        """
        user = self.get_object()
        user.is_active = False
        user.save()
        return Response({
            'message': 'حساب کاربری غیرفعال شد'
        })

    @action(detail=False, methods=['get'], url_path='statistics')
    def statistics(self, request):
        """
        Get user statistics (Admin only)
        GET /api/v1/accounts/users/statistics/
        """
        stats = {
            'total_users': User.objects.count(),
            'active_users': User.objects.filter(is_active=True).count(),
            'students': User.objects.filter(role=User.UserRole.STUDENT).count(),
            'teachers': User.objects.filter(role=User.UserRole.TEACHER).count(),
            'verified_users': User.objects.filter(is_verified=True).count(),
            'new_users_this_month': User.objects.filter(
                created_at__month=timezone.now().month
            ).count(),
        }
        return Response(stats)


class StudentProfileViewSet(viewsets.ModelViewSet):
    """
    Student Profile ViewSet
    """
    queryset = StudentProfile.objects.all()
    serializer_class = StudentProfileSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['education_level', 'is_active_student']
    search_fields = ['user__first_name', 'user__last_name', 'student_number']
    ordering_fields = ['created_at', 'registration_date']

    def get_queryset(self):
        user = self.request.user
        if user.role == User.UserRole.STUDENT:
            return StudentProfile.objects.filter(user=user)
        return StudentProfile.objects.all()

    @action(detail=False, methods=['get'], url_path='my-profile')
    def my_profile(self, request):
        """
        Get current student profile
        GET /api/v1/accounts/students/my-profile/
        """
        try:
            profile = StudentProfile.objects.get(user=request.user)
            serializer = self.get_serializer(profile)
            return Response(serializer.data)
        except StudentProfile.DoesNotExist:
            return Response({
                'error': 'پروفایل دانش آموز یافت نشد'
            }, status=status.HTTP_404_NOT_FOUND)


class TeacherProfileViewSet(viewsets.ModelViewSet):
    """
    Teacher Profile ViewSet
    """
    queryset = TeacherProfile.objects.all()
    serializer_class = TeacherProfileSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'can_teach_online']
    search_fields = ['user__first_name', 'user__last_name', 'employee_code', 'expertise']
    ordering_fields = ['created_at', 'rating', 'experience_years']

    @action(detail=False, methods=['get'], url_path='my-profile')
    def my_profile(self, request):
        """
        Get current teacher profile
        GET /api/v1/accounts/teachers/my-profile/
        """
        try:
            profile = TeacherProfile.objects.get(user=request.user)
            serializer = self.get_serializer(profile)
            return Response(serializer.data)
        except TeacherProfile.DoesNotExist:
            return Response({
                'error': 'پروفایل معلم یافت نشد'
            }, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['get'], url_path='top-rated')
    def top_rated(self, request):
        """
        Get top rated teachers
        GET /api/v1/accounts/teachers/top-rated/
        """
        teachers = TeacherProfile.objects.filter(
            status=TeacherProfile.TeacherStatus.ACTIVE
        ).order_by('-rating')[:10]
        
        serializer = self.get_serializer(teachers, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'], url_path='schedule')
    def schedule(self, request, pk=None):
        """
        Get teacher's class schedule
        GET /api/v1/accounts/teachers/{id}/schedule/
        """
        teacher = self.get_object()
        # این قسمت بعداً با ماژول courses تکمیل می‌شود
        return Response({
            'message': 'برنامه معلم',
            'teacher_id': str(teacher.id)
        })


class LoginHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Login History ViewSet (Read only)
    """
    queryset = LoginHistory.objects.all()
    serializer_class = LoginHistorySerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['login_successful', 'device_type', 'browser']
    ordering_fields = ['created_at']

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser or user.role == User.UserRole.SUPER_ADMIN:
            return LoginHistory.objects.all()
        return LoginHistory.objects.filter(user=user)

    @action(detail=False, methods=['get'], url_path='my-history')
    def my_history(self, request):
        """
        Get current user's login history
        GET /api/v1/accounts/login-history/my-history/
        """
        history = LoginHistory.objects.filter(user=request.user).order_by('-created_at')[:20]
        serializer = self.get_serializer(history, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='active-sessions')
    def active_sessions(self, request):
        """
        Get active login sessions
        GET /api/v1/accounts/login-history/active-sessions/
        """
        sessions = LoginHistory.objects.filter(
            user=request.user,
            logout_at__isnull=True
        ).order_by('-created_at')
        
        serializer = self.get_serializer(sessions, many=True)
        return Response(serializer.data)