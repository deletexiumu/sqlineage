/**
 * 数据库管理器
 * 处理数据库连接、表结构查询等
 */
export default class DatabaseManager {
  constructor() {
    this.connections = new Map();
    this.schemas = new Map();
  }

  /**
   * 添加数据库连接配置
   */
  addConnection(name, config) {
    this.connections.set(name, {
      name,
      type: config.type || 'hive',
      host: config.host || 'localhost',
      port: config.port || 10000,
      username: config.username || '',
      password: config.password || '',
      database: config.database || 'default',
      connected: false,
      lastConnected: null
    });
  }

  /**
   * 测试数据库连接
   */
  async testConnection(connectionName) {
    const connection = this.connections.get(connectionName);
    if (!connection) {
      throw new Error(`连接 ${connectionName} 不存在`);
    }

    try {
      // 模拟连接测试
      await this.simulateConnection(connection);
      connection.connected = true;
      connection.lastConnected = new Date();
      return { success: true, message: '连接成功' };
    } catch (error) {
      connection.connected = false;
      throw error;
    }
  }

  /**
   * 模拟数据库连接
   */
  async simulateConnection(connection) {
    return new Promise((resolve, reject) => {
      // 模拟网络延迟
      setTimeout(() => {
        if (connection.host === 'localhost' || connection.host.includes('test')) {
          resolve();
        } else {
          reject(new Error('无法连接到数据库服务器'));
        }
      }, 1000);
    });
  }

  /**
   * 获取表结构
   */
  async getTableSchema(connectionName, tableName) {
    const connection = this.connections.get(connectionName);
    if (!connection) {
      throw new Error(`连接 ${connectionName} 不存在`);
    }

    const cacheKey = `${connectionName}.${tableName}`;
    if (this.schemas.has(cacheKey)) {
      return this.schemas.get(cacheKey);
    }

    try {
      const schema = await this.fetchTableSchema(connection, tableName);
      this.schemas.set(cacheKey, schema);
      return schema;
    } catch (error) {
      throw new Error(`获取表结构失败: ${error.message}`);
    }
  }

  /**
   * 模拟获取表结构
   */
  async fetchTableSchema(connection, tableName) {
    return new Promise((resolve) => {
      setTimeout(() => {
        // 返回模拟的表结构
        const schema = {
          tableName,
          database: connection.database,
          columns: this.generateMockColumns(tableName),
          partitions: [],
          properties: {
            tableType: 'EXTERNAL',
            location: `/data/${tableName}`,
            fileFormat: 'PARQUET'
          },
          createTime: new Date('2024-01-01'),
          lastModified: new Date()
        };
        resolve(schema);
      }, 500);
    });
  }

  /**
   * 生成模拟字段
   */
  generateMockColumns(tableName) {
    const baseColumns = [
      { name: 'id', type: 'BIGINT', comment: '主键ID', nullable: false },
      { name: 'created_time', type: 'TIMESTAMP', comment: '创建时间', nullable: false },
      { name: 'updated_time', type: 'TIMESTAMP', comment: '更新时间', nullable: true }
    ];

    // 根据表名生成特定字段
    const specificColumns = this.getTableSpecificColumns(tableName);
    
    return [...baseColumns, ...specificColumns];
  }

  /**
   * 根据表名生成特定字段
   */
  getTableSpecificColumns(tableName) {
    const lowerName = tableName.toLowerCase();
    
    if (lowerName.includes('user')) {
      return [
        { name: 'user_id', type: 'BIGINT', comment: '用户ID', nullable: false },
        { name: 'username', type: 'STRING', comment: '用户名', nullable: false },
        { name: 'email', type: 'STRING', comment: '邮箱', nullable: true },
        { name: 'status', type: 'INT', comment: '状态', nullable: false }
      ];
    }
    
    if (lowerName.includes('order')) {
      return [
        { name: 'order_id', type: 'BIGINT', comment: '订单ID', nullable: false },
        { name: 'user_id', type: 'BIGINT', comment: '用户ID', nullable: false },
        { name: 'amount', type: 'DECIMAL(10,2)', comment: '金额', nullable: false },
        { name: 'status', type: 'STRING', comment: '订单状态', nullable: false }
      ];
    }
    
    if (lowerName.includes('event')) {
      return [
        { name: 'event_id', type: 'BIGINT', comment: '事件ID', nullable: false },
        { name: 'user_id', type: 'BIGINT', comment: '用户ID', nullable: true },
        { name: 'event_type', type: 'STRING', comment: '事件类型', nullable: false },
        { name: 'event_time', type: 'TIMESTAMP', comment: '事件时间', nullable: false }
      ];
    }
    
    // 默认字段
    return [
      { name: 'name', type: 'STRING', comment: '名称', nullable: true },
      { name: 'description', type: 'STRING', comment: '描述', nullable: true },
      { name: 'value', type: 'STRING', comment: '值', nullable: true }
    ];
  }

  /**
   * 获取数据库列表
   */
  async getDatabases(connectionName) {
    const connection = this.connections.get(connectionName);
    if (!connection) {
      throw new Error(`连接 ${connectionName} 不存在`);
    }

    return new Promise((resolve) => {
      setTimeout(() => {
        resolve([
          'default',
          'ods',
          'dw',
          'dm',
          'ads'
        ]);
      }, 300);
    });
  }

  /**
   * 获取表列表
   */
  async getTables(connectionName, database = 'default') {
    const connection = this.connections.get(connectionName);
    if (!connection) {
      throw new Error(`连接 ${connectionName} 不存在`);
    }

    return new Promise((resolve) => {
      setTimeout(() => {
        const tables = this.generateMockTables(database);
        resolve(tables);
      }, 500);
    });
  }

  /**
   * 生成模拟表列表
   */
  generateMockTables(database) {
    const baseTables = {
      'ods': [
        'user_events',
        'order_records',
        'product_info',
        'user_profiles'
      ],
      'dw': [
        'dim_users',
        'dim_products',
        'fact_orders',
        'fact_user_behavior'
      ],
      'dm': [
        'user_behavior_summary',
        'product_sales_summary',
        'daily_metrics'
      ],
      'ads': [
        'user_metrics_report',
        'sales_dashboard',
        'behavior_analysis'
      ],
      'default': [
        'sample_table',
        'test_data'
      ]
    };

    return baseTables[database] || baseTables['default'];
  }

  /**
   * 执行SQL查询
   */
  async executeQuery(connectionName, sql, options = {}) {
    const connection = this.connections.get(connectionName);
    if (!connection) {
      throw new Error(`连接 ${connectionName} 不存在`);
    }

    const { limit = 100, timeout = 30000 } = options;

    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        reject(new Error('查询超时'));
      }, timeout);

      setTimeout(() => {
        clearTimeout(timer);
        
        // 模拟查询结果
        const result = {
          sql,
          columns: [
            { name: 'id', type: 'BIGINT' },
            { name: 'name', type: 'STRING' },
            { name: 'value', type: 'DOUBLE' }
          ],
          rows: Array.from({ length: Math.min(limit, 10) }, (_, i) => [
            i + 1,
            `record_${i + 1}`,
            Math.random() * 100
          ]),
          totalRows: limit,
          executionTime: Math.random() * 1000 + 500
        };
        
        resolve(result);
      }, 1000);
    });
  }

  /**
   * 保存DDL语句
   */
  async saveDDL(tableName, ddl, metadata = {}) {
    const record = {
      tableName,
      ddl,
      metadata,
      savedAt: new Date(),
      version: 1
    };

    // 模拟保存到本地存储或数据库
    const key = `ddl_${tableName}`;
    localStorage.setItem(key, JSON.stringify(record));
    
    return record;
  }

  /**
   * 获取已保存的DDL
   */
  async getSavedDDL(tableName) {
    const key = `ddl_${tableName}`;
    const saved = localStorage.getItem(key);
    
    if (saved) {
      return JSON.parse(saved);
    }
    
    return null;
  }

  /**
   * 获取连接状态
   */
  getConnectionStatus(connectionName) {
    const connection = this.connections.get(connectionName);
    return connection ? {
      name: connection.name,
      type: connection.type,
      connected: connection.connected,
      lastConnected: connection.lastConnected
    } : null;
  }

  /**
   * 获取所有连接
   */
  getAllConnections() {
    return Array.from(this.connections.values()).map(conn => ({
      name: conn.name,
      type: conn.type,
      host: conn.host,
      database: conn.database,
      connected: conn.connected,
      lastConnected: conn.lastConnected
    }));
  }

  /**
   * 删除连接
   */
  removeConnection(connectionName) {
    return this.connections.delete(connectionName);
  }

  /**
   * 清空缓存
   */
  clearCache() {
    this.schemas.clear();
  }

  /**
   * 获取连接列表
   */
  listConnections() {
    return Array.from(this.connections.values());
  }

  /**
   * 批量获取表结构
   */
  async batchGetTableSchemas(connectionName, tableNames) {
    const schemas = {};
    
    for (const tableName of tableNames) {
      try {
        const schema = await this.getTableSchema(connectionName, tableName);
        schemas[tableName] = schema;
      } catch (error) {
        console.warn(`Failed to get schema for table ${tableName}:`, error);
        schemas[tableName] = null;
      }
    }
    
    return schemas;
  }

  /**
   * 从本地存储加载DDL
   */
  loadDDLFromLocalStorage() {
    try {
      const keys = Object.keys(localStorage);
      const ddlKeys = keys.filter(key => key.startsWith('ddl_'));
      
      console.log(`Loaded ${ddlKeys.length} DDL records from localStorage`);
      
      ddlKeys.forEach(key => {
        const ddlData = localStorage.getItem(key);
        if (ddlData) {
          try {
            const parsed = JSON.parse(ddlData);
            console.log(`DDL for ${parsed.tableName}:`, parsed);
          } catch (error) {
            console.warn(`Failed to parse DDL data for key ${key}:`, error);
          }
        }
      });
    } catch (error) {
      console.warn('Failed to load DDL from localStorage:', error);
    }
  }
} 