"""
WebSocket消费者，实现LSP协议通信
"""
import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .sql_language_server import sql_language_server

logger = logging.getLogger(__name__)


class SQLLanguageServerConsumer(AsyncWebsocketConsumer):
    """SQL Language Server WebSocket Consumer"""
    
    async def connect(self):
        """WebSocket连接建立"""
        await self.accept()
        logger.info("SQL Language Server WebSocket connected")
        
        # 发送初始化能力
        await self.send_response(None, {
            "capabilities": sql_language_server.get_capabilities()
        })
    
    async def disconnect(self, close_code):
        """WebSocket连接断开"""
        logger.info(f"SQL Language Server WebSocket disconnected: {close_code}")
    
    async def receive(self, text_data):
        """接收客户端消息"""
        try:
            message = json.loads(text_data)
            method = message.get('method')
            params = message.get('params', {})
            request_id = message.get('id')
            
            logger.debug(f"Received LSP message: {method}")
            
            # 路由到相应的处理方法
            if method == 'textDocument/completion':
                result = await self.handle_completion(params)
            elif method == 'textDocument/hover':
                result = await self.handle_hover(params)
            elif method == 'textDocument/publishDiagnostics':
                result = await self.handle_diagnostics(params)
            elif method == 'workspace/refreshMetadata':
                result = await self.handle_refresh_metadata(params)
            elif method == 'initialize':
                result = await self.handle_initialize(params)
            else:
                result = {"error": f"Unknown method: {method}"}
            
            # 发送响应
            await self.send_response(request_id, result)
            
        except Exception as e:
            logger.error(f"Error processing LSP message: {str(e)}")
            await self.send_error(request_id if 'request_id' in locals() else None, str(e))
    
    async def send_response(self, request_id, result):
        """发送LSP响应"""
        response = {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": result
        }
        await self.send(text_data=json.dumps(response))
    
    async def send_error(self, request_id, error_message):
        """发送错误响应"""
        response = {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": -32603,  # Internal error
                "message": error_message
            }
        }
        await self.send(text_data=json.dumps(response))
    
    async def handle_initialize(self, params):
        """处理初始化请求"""
        return {
            "capabilities": sql_language_server.get_capabilities(),
            "serverInfo": {
                "name": "SQL Language Server",
                "version": "1.0.0"
            }
        }
    
    @database_sync_to_async
    def handle_completion(self, params):
        """处理自动补全请求"""
        try:
            text_document = params.get('textDocument', {})
            position = params.get('position', {})
            
            # 获取文档内容（这里需要从客户端传递）
            document_text = params.get('documentText', '')
            line = position.get('line', 0)
            character = position.get('character', 0)
            
            # 调用LSP服务器获取补全建议
            items = sql_language_server.provide_completion(document_text, line, character)
            
            return {
                "isIncomplete": False,
                "items": items
            }
            
        except Exception as e:
            logger.error(f"Error in handle_completion: {str(e)}")
            return {"isIncomplete": False, "items": []}
    
    @database_sync_to_async
    def handle_hover(self, params):
        """处理悬停信息请求"""
        try:
            position = params.get('position', {})
            document_text = params.get('documentText', '')
            line = position.get('line', 0)
            character = position.get('character', 0)
            
            # 调用LSP服务器获取悬停信息
            hover_info = sql_language_server.provide_hover(document_text, line, character)
            
            return hover_info
            
        except Exception as e:
            logger.error(f"Error in handle_hover: {str(e)}")
            return None
    
    @database_sync_to_async
    def handle_diagnostics(self, params):
        """处理诊断请求"""
        try:
            document_text = params.get('documentText', '')
            
            # 调用LSP服务器获取诊断信息
            diagnostics = sql_language_server.provide_diagnostics(document_text)
            
            return {
                "uri": params.get('uri', ''),
                "diagnostics": diagnostics
            }
            
        except Exception as e:
            logger.error(f"Error in handle_diagnostics: {str(e)}")
            return {"uri": "", "diagnostics": []}
    
    @database_sync_to_async
    def handle_refresh_metadata(self, params):
        """处理元数据刷新请求"""
        try:
            result = sql_language_server.refresh_metadata()
            return result
            
        except Exception as e:
            logger.error(f"Error in handle_refresh_metadata: {str(e)}")
            return {"status": "error", "message": str(e)}