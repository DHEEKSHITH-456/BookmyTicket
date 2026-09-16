from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from movies import dashboard_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('dashboard/', dashboard_views.admin_dashboard, name='admin_dashboard_root'),
    path('dashboard/export/<str:report_type>/', dashboard_views.export_dashboard_csv, name='export_dashboard_csv_root'),
    path('users/', include('users.urls')),
    path('',include('users.urls')),
    path('movies/', include('movies.urls')),
]

from django.urls import re_path
from django.views.static import serve

urlpatterns += [
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
]
