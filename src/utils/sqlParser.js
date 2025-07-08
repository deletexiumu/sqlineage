/**
 * Hive SQL解析器
 * 支持多语句解析、注释过滤、表和字段提取
 */
export default class HiveSqlParser {
  constructor() {
    this.keywords = [
      'SELECT', 'FROM', 'WHERE', 'JOIN', 'LEFT', 'RIGHT', 'INNER', 'OUTER',
      'GROUP', 'ORDER', 'HAVING', 'INSERT', 'UPDATE', 'DELETE', 'CREATE',
      'ALTER', 'DROP', 'WITH', 'AS', 'ON', 'AND', 'OR', 'NOT', 'IN',
      'EXISTS', 'BETWEEN', 'LIKE', 'IS', 'NULL', 'DISTINCT', 'UNION',
      'CASE', 'WHEN', 'THEN', 'ELSE', 'END', 'LIMIT', 'OFFSET'
    ];
  }

  /**
   * 分割SQL语句
   */
  splitSqlStatements(sql) {
    if (!sql || typeof sql !== 'string') return [];
    
    const statements = [];
    let current = '';
    let inString = false;
    let stringChar = '';
    let inComment = false;
    
    for (let i = 0; i < sql.length; i++) {
      const char = sql[i];
      const nextChar = sql[i + 1];
      
      // 处理注释
      if (!inString && !inComment && char === '-' && nextChar === '-') {
        inComment = 'line';
        i++; // 跳过下一个字符
        continue;
      }
      
      if (!inString && !inComment && char === '/' && nextChar === '*') {
        inComment = 'block';
        i++; // 跳过下一个字符
        continue;
      }
      
      if (inComment === 'line' && char === '\n') {
        inComment = false;
        current += char;
        continue;
      }
      
      if (inComment === 'block' && char === '*' && nextChar === '/') {
        inComment = false;
        i++; // 跳过下一个字符
        continue;
      }
      
      if (inComment) continue;
      
      // 处理字符串
      if (!inString && (char === "'" || char === '"')) {
        inString = true;
        stringChar = char;
      } else if (inString && char === stringChar) {
        if (i > 0 && sql[i - 1] !== '\\') {
          inString = false;
          stringChar = '';
        }
      }
      
      // 处理语句分隔符
      if (!inString && char === ';') {
        const trimmed = current.trim();
        if (trimmed) {
          statements.push(trimmed);
        }
        current = '';
        continue;
      }
      
      current += char;
    }
    
    // 添加最后一个语句
    const trimmed = current.trim();
    if (trimmed) {
      statements.push(trimmed);
    }
    
    return statements.filter(stmt => stmt.length > 0);
  }

  /**
   * 解析单个SQL语句
   */
  parseStatement(sql) {
    if (!sql || typeof sql !== 'string') return null;
    
    const cleanedSql = this.removeComments(sql);
    const statementType = this.getStatementType(cleanedSql);
    
    const result = {
      type: statementType,
      original: sql,
      cleaned: cleanedSql,
      tables: this.extractTables(cleanedSql),
      columns: this.extractColumns(cleanedSql)
    };
    
    if (statementType === 'CREATE') {
      result.createInfo = this.parseCreateStatement(cleanedSql);
    } else if (statementType === 'INSERT' || statementType === 'SELECT') {
      result.selectInfo = this.parseSelectStatement(cleanedSql);
    }
    
    return result;
  }

  /**
   * 移除注释
   */
  removeComments(sql) {
    let result = sql;
    
    // 移除单行注释
    result = result.replace(/--.*$/gm, '');
    
    // 移除多行注释
    result = result.replace(/\/\*[\s\S]*?\*\//g, '');
    
    // 清理多余的空白字符
    result = result.replace(/\s+/g, ' ').trim();
    
    return result;
  }

  /**
   * 获取语句类型
   */
  getStatementType(sql) {
    const upperSql = sql.toUpperCase().trim();
    
    if (upperSql.startsWith('SELECT')) return 'SELECT';
    if (upperSql.startsWith('INSERT')) return 'INSERT';
    if (upperSql.startsWith('UPDATE')) return 'UPDATE';
    if (upperSql.startsWith('DELETE')) return 'DELETE';
    if (upperSql.startsWith('CREATE')) return 'CREATE';
    if (upperSql.startsWith('ALTER')) return 'ALTER';
    if (upperSql.startsWith('DROP')) return 'DROP';
    if (upperSql.startsWith('WITH')) return 'WITH';
    
    return 'UNKNOWN';
  }

  /**
   * 提取表名
   */
  extractTables(sql) {
    const tables = new Set();
    const upperSql = sql.toUpperCase();
    
    // 提取FROM子句中的表
    const fromPattern = /FROM\s+([^\s,\(]+(?:\s*,\s*[^\s,\(]+)*)/gi;
    const fromMatches = sql.match(fromPattern);
    if (fromMatches) {
      fromMatches.forEach(match => {
        const tableNames = match.replace(/FROM\s+/i, '').split(',');
        tableNames.forEach(name => {
          const cleanName = name.trim().split(/\s+/)[0];
          if (cleanName && !this.isKeyword(cleanName)) {
            tables.add(this.normalizeTableName(cleanName));
          }
        });
      });
    }
    
    // 提取JOIN子句中的表
    const joinPattern = /JOIN\s+([^\s\(]+)/gi;
    const joinMatches = sql.match(joinPattern);
    if (joinMatches) {
      joinMatches.forEach(match => {
        const tableName = match.replace(/JOIN\s+/i, '').trim().split(/\s+/)[0];
        if (tableName && !this.isKeyword(tableName)) {
          tables.add(this.normalizeTableName(tableName));
        }
      });
    }
    
    // 提取INSERT INTO中的表
    const insertPattern = /INSERT\s+(?:OVERWRITE\s+)?(?:INTO\s+)?(?:TABLE\s+)?([^\s\(]+)/i;
    const insertMatch = sql.match(insertPattern);
    if (insertMatch) {
      const tableName = insertMatch[1].trim();
      if (tableName && !this.isKeyword(tableName)) {
        tables.add(this.normalizeTableName(tableName));
      }
    }
    
    // 提取CREATE TABLE中的表
    const createPattern = /CREATE\s+(?:EXTERNAL\s+)?TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?([^\s\(]+)/i;
    const createMatch = sql.match(createPattern);
    if (createMatch) {
      const tableName = createMatch[1].trim();
      if (tableName && !this.isKeyword(tableName)) {
        tables.add(this.normalizeTableName(tableName));
      }
    }
    
    return Array.from(tables);
  }

  /**
   * 提取字段名
   */
  extractColumns(sql) {
    const columns = new Set();
    
    // 简单的字段提取（可以根据需要扩展）
    const selectPattern = /SELECT\s+(.*?)\s+FROM/is;
    const selectMatch = sql.match(selectPattern);
    
    if (selectMatch) {
      const columnsPart = selectMatch[1];
      const columnNames = columnsPart.split(',');
      
      columnNames.forEach(col => {
        const cleanCol = col.trim().split(/\s+/)[0];
        if (cleanCol && cleanCol !== '*' && !this.isKeyword(cleanCol)) {
          // 提取字段名（去掉表名前缀）
          const fieldName = cleanCol.includes('.') ? 
            cleanCol.split('.').pop() : cleanCol;
          columns.add(fieldName);
        }
      });
    }
    
    return Array.from(columns);
  }

  /**
   * 解析CREATE语句
   */
  parseCreateStatement(sql) {
    const result = {
      tableName: '',
      columns: [],
      partitions: [],
      properties: {}
    };
    
    // 提取表名
    const tablePattern = /CREATE\s+(?:EXTERNAL\s+)?TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?([^\s\(]+)/i;
    const tableMatch = sql.match(tablePattern);
    if (tableMatch) {
      result.tableName = this.normalizeTableName(tableMatch[1]);
    }
    
    // 提取字段定义
    const columnsPattern = /\(\s*(.*?)\s*\)(?:\s*COMMENT|\s*PARTITIONED|\s*STORED|\s*LOCATION|\s*TBLPROPERTIES|\s*$)/is;
    const columnsMatch = sql.match(columnsPattern);
    if (columnsMatch) {
      const columnsDef = columnsMatch[1];
      const columns = this.parseColumnDefinitions(columnsDef);
      result.columns = columns;
    }
    
    return result;
  }

  /**
   * 解析字段定义
   */
  parseColumnDefinitions(columnsDef) {
    const columns = [];
    const lines = columnsDef.split(',');
    
    lines.forEach(line => {
      const trimmed = line.trim();
      if (!trimmed) return;
      
      const parts = trimmed.split(/\s+/);
      if (parts.length >= 2) {
        const column = {
          name: parts[0],
          type: parts[1],
          comment: ''
        };
        
        // 提取注释
        const commentMatch = trimmed.match(/COMMENT\s+['"](.*?)['"]/i);
        if (commentMatch) {
          column.comment = commentMatch[1];
        }
        
        columns.push(column);
      }
    });
    
    return columns;
  }

  /**
   * 解析SELECT语句
   */
  parseSelectStatement(sql) {
    return {
      selectFields: this.extractColumns(sql),
      fromTables: this.extractTables(sql)
    };
  }

  /**
   * 标准化表名
   */
  normalizeTableName(tableName) {
    return tableName.replace(/[`"']/g, '').toLowerCase();
  }

  /**
   * 检查是否为关键字
   */
  isKeyword(word) {
    return this.keywords.includes(word.toUpperCase());
  }

  /**
   * 格式化SQL
   */
  formatSql(sql) {
    let formatted = sql;
    
    // 添加换行符
    const keywords = ['SELECT', 'FROM', 'WHERE', 'GROUP BY', 'ORDER BY', 'HAVING'];
    keywords.forEach(keyword => {
      const regex = new RegExp(`\\b${keyword}\\b`, 'gi');
      formatted = formatted.replace(regex, `\n${keyword}`);
    });
    
    // 清理多余的空行
    formatted = formatted.replace(/\n\s*\n/g, '\n').trim();
    
    return formatted;
  }

  /**
   * 解析多个SQL语句 - App.vue中调用的方法
   */
  parseMultipleStatements(sql) {
    const statements = this.splitSqlStatements(sql);
    
    return statements.map(stmt => {
      try {
        const parsed = this.parseStatement(stmt);
        return {
          success: true,
          statement: stmt,
          ast: parsed,
          error: null
        };
      } catch (error) {
        return {
          success: false,
          statement: stmt,
          ast: null,
          error: error.message
        };
      }
    });
  }

  /**
   * 从AST中提取表名 - App.vue中调用的方法
   */
  extractTablesFromAst(ast) {
    if (!ast || !ast.tables) {
      return [];
    }
    
    return ast.tables || [];
  }
} 