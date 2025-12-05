from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

# Swagger/OpenAPI Schema
schema_view = get_schema_view(
    openapi.Info(
        title="Academy Management API",
        default_version='v1',
        description="Complete API documentation for Academy Management System",
        terms_of_service="https://www.google.com/policies/terms/",
        contact=openapi.Contact(email="contact@academy.local"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),
    
    # API Documentation
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    
    # API v1
    path('api/v1/', include('apps.core.urls')),
    path('api/v1/accounts/', include('apps.accounts.urls')),
    path('api/v1/branches/', include('apps.branches.urls')),
    path('api/v1/courses/', include('apps.courses.urls')),
    path('api/v1/enrollments/', include('apps.enrollments.urls')),
    path('api/v1/attendance/', include('apps.attendance.urls')),
    path('api/v1/financial/', include('apps.financial.urls')),
    path('api/v1/notifications/', include('apps.notifications.urls')),
    path('api/v1/lms/', include('apps.lms.urls')),
    path('api/v1/reports/', include('apps.reports.urls')),
    path('api/v1/crm/', include('apps.crm.urls')),
]

# Static and Media files in development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    
    # Debug toolbar
    import debug_toolbar
    urlpatterns = [
        path('__debug__/', include(debug_toolbar.urls)),
    ] + urlpatterns

# Custom Admin
admin.site.site_header = "مدیریت آموزشگاه"
admin.site.site_title = "پنل مدیریت"
admin.site.index_title = "خوش آمدید"