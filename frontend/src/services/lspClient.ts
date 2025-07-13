/**
 * SQL LSP客户端服务
 * 管理WebWorker和LSP通信
 */

import type { CompletionItem, Position } from '../workers/sqlLspWorker'

export interface LSPClientOptions {
  onDiagnostics?: (diagnostics: any[]) => void
  onError?: (error: string) => void
  onConnectionChange?: (connected: boolean) => void
}

export class LSPClient {
  private worker: Worker | null = null
  private requestId = 0
  private pendingRequests = new Map<number, {
    resolve: (value: any) => void
    reject: (error: any) => void
  }>()
  private options: LSPClientOptions
  private isConnected = false
  private lastCompletionTime = 0
  private completionDebounceMs = 300

  constructor(options: LSPClientOptions = {}) {
    this.options = options
    this.initializeWorker()
  }

  private initializeWorker() {
    try {
      // 创建WebWorker
      this.worker = new Worker(
        new URL('../workers/sqlLspWorker.ts', import.meta.url),
        { type: 'module' }
      )

      this.worker.onmessage = (event) => {
        this.handleWorkerMessage(event.data)
      }

      this.worker.onerror = (error) => {
        console.error('LSP Worker error:', error)
        this.options.onError?.('LSP Worker error')
      }

      console.log('SQL LSP Client initialized')
    } catch (error) {
      console.error('Failed to initialize LSP Worker:', error)
      this.options.onError?.('Failed to initialize LSP service')
    }
  }

  private handleWorkerMessage(data: any) {
    const { type, requestId, data: result, error } = data

    switch (type) {
      case 'completion-result':
      case 'hover-result':
      case 'diagnostics-result':
      case 'refresh-metadata-result':
        if (requestId && this.pendingRequests.has(requestId)) {
          const { resolve, reject } = this.pendingRequests.get(requestId)!
          this.pendingRequests.delete(requestId)
          
          if (error) {
            reject(new Error(error))
          } else {
            resolve(result)
          }
        }
        break

      case 'diagnostics':
        // 处理主动推送的诊断信息
        this.options.onDiagnostics?.(result)
        break

      case 'lsp-unavailable':
        this.isConnected = false
        this.options.onConnectionChange?.(false)
        this.options.onError?.('SQL Language Server is unavailable')
        break

      case 'error':
        if (requestId && this.pendingRequests.has(requestId)) {
          const { reject } = this.pendingRequests.get(requestId)!
          this.pendingRequests.delete(requestId)
          reject(new Error(error))
        }
        break

      default:
        console.warn('Unknown worker message type:', type)
    }
  }

  private sendWorkerMessage(type: string, data: any): Promise<any> {
    return new Promise((resolve, reject) => {
      if (!this.worker) {
        reject(new Error('LSP Worker not available'))
        return
      }

      const requestId = ++this.requestId
      this.pendingRequests.set(requestId, { resolve, reject })

      this.worker.postMessage({
        type,
        data: { ...data, requestId }
      })

      // 设置超时
      setTimeout(() => {
        if (this.pendingRequests.has(requestId)) {
          this.pendingRequests.delete(requestId)
          reject(new Error('LSP request timeout'))
        }
      }, 10000)
    })
  }

  /**
   * 获取自动补全建议
   */
  public async getCompletions(documentText: string, position: Position): Promise<CompletionItem[]> {
    try {
      // 防抖：避免过于频繁的请求
      const now = Date.now()
      if (now - this.lastCompletionTime < this.completionDebounceMs) {
        return []
      }
      this.lastCompletionTime = now

      return await this.sendWorkerMessage('completion', {
        documentText,
        position
      })
    } catch (error) {
      console.error('Failed to get completions:', error)
      return []
    }
  }

  /**
   * 获取悬停信息
   */
  public async getHover(documentText: string, position: Position): Promise<any> {
    try {
      return await this.sendWorkerMessage('hover', {
        documentText,
        position
      })
    } catch (error) {
      console.error('Failed to get hover:', error)
      return null
    }
  }

  /**
   * 获取诊断信息
   */
  public async getDiagnostics(documentText: string): Promise<any[]> {
    try {
      return await this.sendWorkerMessage('diagnostics', {
        documentText
      })
    } catch (error) {
      console.error('Failed to get diagnostics:', error)
      return []
    }
  }

  /**
   * 刷新元数据缓存
   */
  public async refreshMetadata(): Promise<void> {
    try {
      await this.sendWorkerMessage('refresh-metadata', {})
    } catch (error) {
      console.error('Failed to refresh metadata:', error)
    }
  }

  /**
   * 销毁LSP客户端
   */
  public dispose() {
    if (this.worker) {
      this.worker.terminate()
      this.worker = null
    }
    this.pendingRequests.clear()
  }

  /**
   * 检查LSP服务是否可用
   */
  public isServiceAvailable(): boolean {
    return this.worker !== null && this.isConnected
  }
}

// Monaco Editor LSP集成工具
export class MonacoLSPIntegration {
  private lspClient: LSPClient
  private editor: any
  private diagnosticsDecorations: string[] = []

  constructor(editor: any, lspClient: LSPClient) {
    this.editor = editor
    this.lspClient = lspClient
    this.setupIntegration()
  }

  private setupIntegration() {
    // 设置自动补全提供者
    this.setupCompletionProvider()
    
    // 设置悬停提供者
    this.setupHoverProvider()
    
    // 设置文档变更监听
    this.setupDocumentChangeListener()
  }

  private setupCompletionProvider() {
    // 注册自动补全提供者
    const monaco = (window as any).monaco
    if (!monaco) return

    monaco.languages.registerCompletionItemProvider('sql', {
      triggerCharacters: ['.', ' ', '\n', '\t'],
      
      provideCompletionItems: async (model: any, position: any, context: any, token: any) => {
        // 检查取消令牌
        if (token.isCancellationRequested) {
          return { suggestions: [] }
        }

        try {
          const documentText = model.getValue()
          const lspPosition = {
            line: position.lineNumber - 1, // Monaco使用1based，LSP使用0based
            character: position.column - 1
          }

          console.log('Monaco: Requesting completions from LSP')
          const completions = await this.lspClient.getCompletions(documentText, lspPosition)
          
          // 再次检查取消令牌
          if (token.isCancellationRequested) {
            return { suggestions: [] }
          }

          console.log('Monaco: Converting completions', completions.length)
          
          // 优化：限制建议数量并快速转换
          const suggestions = completions.slice(0, 10).map((item: CompletionItem) => {
            // 计算正确的插入范围，避免重复文本
            const word = model.getWordUntilPosition(position)
            const range = {
              startLineNumber: position.lineNumber,
              endLineNumber: position.lineNumber,
              startColumn: word.startColumn,
              endColumn: word.endColumn
            }
            
            return {
              label: item.label,
              kind: this.convertLSPKindToMonaco(item.kind || 1),
              detail: item.detail || '',
              documentation: item.documentation ? { value: item.documentation } : undefined,
              insertText: item.insertText || item.label,
              sortText: item.sortText || item.label,
              range: range
            }
          })

          console.log('Monaco: Returning suggestions', suggestions.length)
          return {
            suggestions,
            incomplete: completions.length > 10
          }
        } catch (error) {
          console.error('Completion provider error:', error)
          return { suggestions: [] }
        }
      }
    })
  }

  private setupHoverProvider() {
    const monaco = (window as any).monaco
    if (!monaco) return

    monaco.languages.registerHoverProvider('sql', {
      provideHover: async (model: any, position: any) => {
        try {
          const documentText = model.getValue()
          const lspPosition = {
            line: position.lineNumber - 1,
            character: position.column - 1
          }

          const hover = await this.lspClient.getHover(documentText, lspPosition)
          
          if (hover && hover.contents) {
            return {
              range: new monaco.Range(
                position.lineNumber,
                position.column,
                position.lineNumber,
                position.column
              ),
              contents: [
                { value: hover.contents.value }
              ]
            }
          }
          
          return null
        } catch (error) {
          console.error('Hover provider error:', error)
          return null
        }
      }
    })
  }

  private setupDocumentChangeListener() {
    // 暂时禁用自动诊断更新以提升性能
    // TODO: 在性能优化后重新启用
    console.log('Document change listener setup (diagnostics disabled for performance)')
    
    // let timeoutId: NodeJS.Timeout | null = null
    // 
    // this.editor.onDidChangeModelContent(() => {
    //   // 防抖处理
    //   if (timeoutId) {
    //     clearTimeout(timeoutId)
    //   }
    //   
    //   timeoutId = setTimeout(async () => {
    //     await this.updateDiagnostics()
    //   }, 1000) // 1秒后更新诊断
    // })
  }

  private async updateDiagnostics() {
    try {
      const documentText = this.editor.getValue()
      const diagnostics = await this.lspClient.getDiagnostics(documentText)
      
      this.displayDiagnostics(diagnostics)
    } catch (error) {
      console.error('Failed to update diagnostics:', error)
    }
  }

  private displayDiagnostics(diagnostics: any[]) {
    const monaco = (window as any).monaco
    if (!monaco) return

    // 清除之前的诊断装饰
    this.diagnosticsDecorations = this.editor.deltaDecorations(
      this.diagnosticsDecorations,
      []
    )

    // 添加新的诊断装饰
    const decorations = diagnostics.map(diagnostic => ({
      range: new monaco.Range(
        diagnostic.range.start.line + 1,
        diagnostic.range.start.character + 1,
        diagnostic.range.end.line + 1,
        diagnostic.range.end.character + 1
      ),
      options: {
        className: diagnostic.severity === 1 ? 'sql-error' : 'sql-warning',
        hoverMessage: {
          value: diagnostic.message
        },
        glyphMarginClassName: diagnostic.severity === 1 ? 'sql-error-glyph' : 'sql-warning-glyph'
      }
    }))

    this.diagnosticsDecorations = this.editor.deltaDecorations(
      [],
      decorations
    )
  }

  private convertLSPKindToMonaco(lspKind: number): number {
    const monaco = (window as any).monaco
    if (!monaco) return 1

    // LSP CompletionItemKind 到 Monaco CompletionItemKind 的映射
    const kindMap: { [key: number]: number } = {
      1: monaco.languages.CompletionItemKind.Text,
      2: monaco.languages.CompletionItemKind.Method,
      3: monaco.languages.CompletionItemKind.Function,
      4: monaco.languages.CompletionItemKind.Constructor,
      5: monaco.languages.CompletionItemKind.Field,
      6: monaco.languages.CompletionItemKind.Variable,
      7: monaco.languages.CompletionItemKind.Class,
      8: monaco.languages.CompletionItemKind.Interface,
      9: monaco.languages.CompletionItemKind.Module,
      10: monaco.languages.CompletionItemKind.Property,
      11: monaco.languages.CompletionItemKind.Unit,
      12: monaco.languages.CompletionItemKind.Value,
      13: monaco.languages.CompletionItemKind.Enum,
      14: monaco.languages.CompletionItemKind.Keyword,
      15: monaco.languages.CompletionItemKind.Snippet,
      16: monaco.languages.CompletionItemKind.Color,
      17: monaco.languages.CompletionItemKind.File,
      18: monaco.languages.CompletionItemKind.Reference
    }

    return kindMap[lspKind] || monaco.languages.CompletionItemKind.Text
  }

  public dispose() {
    // 清理诊断装饰
    if (this.diagnosticsDecorations.length > 0) {
      this.editor.deltaDecorations(this.diagnosticsDecorations, [])
    }
  }
}

export default LSPClient