from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import HiveTableViewSet, BusinessMappingViewSet, MetadataImportViewSet, HiveConnectionViewSet

router = DefaultRouter()
router.register(r'tables', HiveTableViewSet)
router.register(r'business-mappings', BusinessMappingViewSet)
router.register(r'import', MetadataImportViewSet, basename='metadata-import')
router.register(r'hive-connection', HiveConnectionViewSet, basename='hive-connection')

urlpatterns = [
    path('', include(router.urls)),
]