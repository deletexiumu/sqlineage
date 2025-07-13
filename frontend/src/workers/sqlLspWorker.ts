/**
 * SQL Language Server Protocol WebWorker
 * 处理与后端LSP服务的WebSocket通信
 */

interface LSPMessage {
  jsonrpc: string
  id?: string | number
  method?: string
  params?: any
  result?: any
  error?: any
}

interface CompletionItem {
  label: string
  kind: number
  detail?: string
  documentation?: string
  insertText?: string
  sortText?: string
}

interface Position {
  line: number
  character: number
}

class SQLLSPWorker {
  private ws: WebSocket | null = null
  private requestId = 0
  private pendingRequests = new Map<string | number, (result: any) => void>()
  private isConnected = false
  private reconnectAttempts = 0
  private maxReconnectAttempts = 5

  constructor() {
    this.connect()
  }

  private connect() {
    const wsUrl = `ws://localhost:8000/ws/sql-lsp/`
    
    try {
      this.ws = new WebSocket(wsUrl)
      
      this.ws.onopen = () => {
        console.log('SQL LSP WebSocket connected')
        this.isConnected = true
        this.reconnectAttempts = 0
        
        // 发送初始化请求
        this.sendRequest('initialize', {
          processId: null,
          clientInfo: {
            name: 'HiicHiveIDE SQL Editor',
            version: '1.0.0'
          },
          capabilities: {
            textDocument: {
              completion: {
                dynamicRegistration: false,
                completionItem: {
                  snippetSupport: false
                }
              },
              hover: {
                dynamicRegistration: false,
                contentFormat: ['markdown', 'plaintext']
              }
            }
          }
        })
      }
      
      this.ws.onmessage = (event) => {
        try {
          const message: LSPMessage = JSON.parse(event.data)
          this.handleMessage(message)
        } catch (error) {
          console.error('Failed to parse LSP message:', error)
        }
      }
      
      this.ws.onclose = () => {
        console.log('SQL LSP WebSocket disconnected')
        this.isConnected = false
        this.attemptReconnect()
      }
      
      this.ws.onerror = (error) => {
        console.error('SQL LSP WebSocket error:', error)
      }
      
    } catch (error) {
      console.error('Failed to create WebSocket connection:', error)
      this.attemptReconnect()
    }
  }

  private attemptReconnect() {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++
      const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts - 1), 10000)
      
      console.log(`Attempting to reconnect to SQL LSP (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts}) in ${delay}ms`)
      
      setTimeout(() => {
        this.connect()
      }, delay)
    } else {
      console.error('Max reconnection attempts reached. SQL LSP features will be disabled.')
      // 通知主线程LSP服务不可用
      self.postMessage({
        type: 'lsp-unavailable',
        message: 'SQL Language Server is unavailable'
      })
    }
  }

  private handleMessage(message: LSPMessage) {
    if (message.id !== undefined && this.pendingRequests.has(message.id)) {
      // 处理响应
      const callback = this.pendingRequests.get(message.id)!
      callback(message.result || message.error)
      this.pendingRequests.delete(message.id)
    } else if (message.method) {
      // 处理通知
      this.handleNotification(message)
    }
  }

  private handleNotification(message: LSPMessage) {
    // 处理来自服务器的通知
    switch (message.method) {
      case 'textDocument/publishDiagnostics':
        self.postMessage({
          type: 'diagnostics',
          data: message.params
        })
        break
      default:
        console.log('Unhandled LSP notification:', message.method)
    }
  }

  private sendRequest(method: string, params: any): Promise<any> {
    return new Promise((resolve, reject) => {
      if (!this.isConnected || !this.ws) {
        reject(new Error('LSP WebSocket not connected'))
        return
      }

      const id = ++this.requestId
      const message: LSPMessage = {
        jsonrpc: '2.0',
        id,
        method,
        params
      }

      this.pendingRequests.set(id, resolve)
      
      try {
        this.ws.send(JSON.stringify(message))
        
        // 设置超时
        setTimeout(() => {
          if (this.pendingRequests.has(id)) {
            this.pendingRequests.delete(id)
            reject(new Error('LSP request timeout'))
          }
        }, 10000)
        
      } catch (error) {
        this.pendingRequests.delete(id)
        reject(error)
      }
    })
  }

  public async getCompletions(documentText: string, position: Position): Promise<CompletionItem[]> {
    try {
      if (!this.isConnected) {
        return []
      }

      const result = await this.sendRequest('textDocument/completion', {
        textDocument: {
          uri: 'inmemory://sql-editor'
        },
        position,
        documentText // 将文档内容包含在请求中
      })

      return result?.items || []
    } catch (error) {
      console.error('Failed to get completions:', error)
      return []
    }
  }

  public async getHover(documentText: string, position: Position): Promise<any> {
    try {
      if (!this.isConnected) {
        return null
      }

      const result = await this.sendRequest('textDocument/hover', {
        textDocument: {
          uri: 'inmemory://sql-editor'
        },
        position,
        documentText
      })

      return result
    } catch (error) {
      console.error('Failed to get hover:', error)
      return null
    }
  }

  public async getDiagnostics(documentText: string): Promise<any[]> {
    try {
      if (!this.isConnected) {
        return []
      }

      const result = await this.sendRequest('textDocument/publishDiagnostics', {
        uri: 'inmemory://sql-editor',
        documentText
      })

      return result?.diagnostics || []
    } catch (error) {
      console.error('Failed to get diagnostics:', error)
      return []
    }
  }

  public async refreshMetadata(): Promise<void> {
    try {
      if (!this.isConnected) {
        return
      }

      await this.sendRequest('workspace/refreshMetadata', {})
    } catch (error) {
      console.error('Failed to refresh metadata:', error)
    }
  }
}

// 创建LSP客户端实例
const lspClient = new SQLLSPWorker()

// 处理来自主线程的消息
self.onmessage = async (event) => {
  const { type, data } = event.data

  try {
    switch (type) {
      case 'completion':
        const completions = await lspClient.getCompletions(data.documentText, data.position)
        self.postMessage({
          type: 'completion-result',
          requestId: data.requestId,
          data: completions
        })
        break

      case 'hover':
        const hover = await lspClient.getHover(data.documentText, data.position)
        self.postMessage({
          type: 'hover-result',
          requestId: data.requestId,
          data: hover
        })
        break

      case 'diagnostics':
        const diagnostics = await lspClient.getDiagnostics(data.documentText)
        self.postMessage({
          type: 'diagnostics-result',
          requestId: data.requestId,
          data: diagnostics
        })
        break

      case 'refresh-metadata':
        await lspClient.refreshMetadata()
        self.postMessage({
          type: 'refresh-metadata-result',
          requestId: data.requestId,
          data: { success: true }
        })
        break

      default:
        console.warn('Unknown message type:', type)
    }
  } catch (error) {
    self.postMessage({
      type: 'error',
      requestId: data.requestId,
      error: error instanceof Error ? error.message : 'Unknown error'
    })
  }
}

// 导出类型定义
export type { CompletionItem, Position }