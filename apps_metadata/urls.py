from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import HiveTableViewSet, BusinessMappingViewSet

router = DefaultRouter()
router.register(r'tables', HiveTableViewSet)
router.register(r'business-mappings', BusinessMappingViewSet)

urlpatterns = [
    path('', include(router.urls)),
]