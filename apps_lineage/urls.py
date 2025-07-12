from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import LineageRelationViewSet, LineageParseJobViewSet

router = DefaultRouter()
router.register(r'relations', LineageRelationViewSet)
router.register(r'jobs', LineageParseJobViewSet)

urlpatterns = [
    path('', include(router.urls)),
]