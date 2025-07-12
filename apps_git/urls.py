from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import GitRepoViewSet, UserViewSet

router = DefaultRouter()
router.register(r'repos', GitRepoViewSet, basename='gitrepo')
router.register(r'users', UserViewSet)

urlpatterns = [
    path('', include(router.urls)),
]