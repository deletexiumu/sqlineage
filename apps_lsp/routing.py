"""
WebSocket路由配置
"""
from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/sql-lsp/$', consumers.SQLLanguageServerConsumer.as_asgi()),
]