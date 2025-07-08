/**
 * 血缘关系分析器
 * 分析SQL语句中的表和字段依赖关系
 */
export default class LineageAnalyzer {
  constructor() {
    this.relationships = [];
    this.tables = new Map();
    this.fieldMappings = [];
  }

  /**
   * 分析SQL语句的血缘关系
   */
  analyze(parsedStatements) {
    this.reset();
    
    if (!Array.isArray(parsedStatements)) {
      return this.getResult();
    }

    // 分析每个语句
    parsedStatements.forEach((statement, index) => {
      this.analyzeStatement(statement, index);
    });

    return this.getResult();
  }

  /**
   * 重置分析结果
   */
  reset() {
    this.relationships = [];
    this.tables.clear();
    this.fieldMappings = [];
  }

  /**
   * 分析单个语句
   */
  analyzeStatement(statement, index) {
    if (!statement || !statement.type) return;

    switch (statement.type) {
      case 'CREATE':
        this.analyzeCreateStatement(statement, index);
        break;
      case 'INSERT':
        this.analyzeInsertStatement(statement, index);
        break;
      case 'SELECT':
        this.analyzeSelectStatement(statement, index);
        break;
      default:
        // 处理其他类型的语句
        break;
    }
  }

  /**
   * 分析CREATE语句
   */
  analyzeCreateStatement(statement, index) {
    try {
      console.log('分析CREATE语句:', statement.cleaned.substring(0, 100) + '...');
      
      // 提取CREATE TABLE中的表名
      const tables = this.extractCreateTables(statement.cleaned);
      console.log('提取到的CREATE TABLE表名:', tables);
      
      tables.forEach(tableName => {
        // 解析字段定义
        const columns = this.parseCreateTableColumns(statement.original);
        console.log(`表 ${tableName} 解析到 ${columns.length} 个字段`);
        
        this.addTable(tableName, {
          type: 'target',
          statement: index,
          columns: columns,
          sqlType: 'CREATE'
        });
      });
    } catch (error) {
      console.error('分析CREATE语句时出错:', error);
    }
  }

  /**
   * 提取CREATE TABLE中的表名
   */
  extractCreateTables(sql) {
    const tables = [];
    
    // CREATE TABLE pattern
    const createPattern = /CREATE\s+(?:EXTERNAL\s+)?TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?([^\s\(]+)/i;
    const createMatch = sql.match(createPattern);
    if (createMatch) {
      tables.push(this.normalizeTableName(createMatch[1]));
    }
    
    return tables;
  }

  /**
   * 解析CREATE TABLE中的字段定义
   */
  parseCreateTableColumns(sql) {
    const columns = [];
    
    try {
      // 更强健的字段定义区域提取，支持多种语法
      let createMatch = sql.match(/CREATE\s+(?:EXTERNAL\s+)?TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?[^\s(]+\s*\(\s*([\s\S]*?)\s*\)\s*(?:COMMENT|PARTITIONED|CLUSTERED|STORED|ROW|LOCATION|TBLPROPERTIES|$)/i);
      
      if (!createMatch) {
        // 尝试更简单的匹配模式
        createMatch = sql.match(/CREATE\s+(?:EXTERNAL\s+)?TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?[^\s(]+\s*\(\s*([\s\S]*?)\s*\)\s*/i);
      }
      
      if (!createMatch) {
        console.warn('无法提取CREATE TABLE字段定义区域');
        return columns;
      }
      
      const columnDefinitions = createMatch[1];
      console.log('提取到的字段定义区域:', columnDefinitions.substring(0, 200) + '...');
      
      // 按逗号分割，但要考虑嵌套括号
      const lines = this.splitColumnDefinitions(columnDefinitions);
      console.log('分割后的字段定义行数:', lines.length);
      
      lines.forEach((line, index) => {
        const cleanLine = line.trim();
        if (!cleanLine || cleanLine.toUpperCase().startsWith('CONSTRAINT') || 
            cleanLine.toUpperCase().startsWith('PRIMARY') ||
            cleanLine.toUpperCase().startsWith('FOREIGN')) {
          return;
        }
        
        // 改进的字段解析，支持反引号和复杂类型
        // 支持格式：`field_name` TYPE COMMENT 'comment'
        const columnMatch = cleanLine.match(/^[`]?([a-zA-Z_][a-zA-Z0-9_]*)[`]?\s+([^\s]+(?:\s*\([^)]*\))?)\s*(?:COMMENT\s+['"](.*?)['"])?/i);
        
        if (columnMatch) {
          const columnName = columnMatch[1];
          let columnType = columnMatch[2];
          const comment = columnMatch[3] || '';
          
          // 清理字段类型中的额外空格
          columnType = columnType.trim();
          
          console.log(`解析字段 ${index + 1}: ${columnName} - ${columnType}`);
          
          columns.push({
            name: columnName,
            type: columnType,
            comment: comment
          });
        } else {
          console.warn('无法解析字段定义:', cleanLine.substring(0, 100));
        }
      });
      
      console.log(`成功解析 ${columns.length} 个字段`);
      
    } catch (error) {
      console.error('解析CREATE TABLE字段时出错:', error);
    }
    
    return columns;
  }

  /**
   * 分割字段定义，正确处理嵌套括号
   */
  splitColumnDefinitions(columnDefs) {
    const definitions = [];
    let current = '';
    let parenCount = 0;
    let inString = false;
    let stringChar = '';
    
    for (let i = 0; i < columnDefs.length; i++) {
      const char = columnDefs[i];
      
      if (!inString && (char === '"' || char === "'")) {
        inString = true;
        stringChar = char;
      } else if (inString && char === stringChar) {
        inString = false;
        stringChar = '';
      } else if (!inString) {
        if (char === '(') {
          parenCount++;
        } else if (char === ')') {
          parenCount--;
        } else if (char === ',' && parenCount === 0) {
          definitions.push(current.trim());
          current = '';
          continue;
        }
      }
      
      current += char;
    }
    
    if (current.trim()) {
      definitions.push(current.trim());
    }
    
    return definitions;
  }

  /**
   * 分析INSERT语句
   */
  analyzeInsertStatement(statement, index) {
    try {
      console.log('分析INSERT语句:', statement.cleaned.substring(0, 100) + '...');
      
      // 从SQL中提取目标表和源表
      const targetTables = this.extractTargetTables(statement.cleaned);
      const sourceTables = this.extractSourceTables(statement.cleaned);
      
      console.log('目标表:', targetTables);
      console.log('源表:', sourceTables);

      // 先分析SELECT字段，提取源表字段信息
      const sourceTableFields = this.extractSourceTableFields(statement);
      console.log('提取到的源表字段信息:', sourceTableFields);

      // 添加目标表
      targetTables.forEach(tableName => {
        this.addTable(tableName, {
          type: 'target',
          statement: index,
          sqlType: 'INSERT'
        });
      });

      // 添加源表，并设置字段信息
      sourceTables.forEach(tableName => {
        const normalizedName = this.normalizeTableName(tableName);
        const tableFields = sourceTableFields[normalizedName] || [];
        
        console.log(`准备为源表 ${tableName} (标准化: ${normalizedName}) 设置字段:`, tableFields);
        console.log(`源表字段信息键值:`, Object.keys(sourceTableFields));
        
        this.addTable(tableName, {
          type: 'source',
          statement: index,
          sqlType: 'INSERT',
          columns: tableFields
        });
        
        console.log(`为源表 ${tableName} 设置了 ${tableFields.length} 个字段`);
      });

      // 建立表级关系和字段级关系
      targetTables.forEach(target => {
        sourceTables.forEach(source => {
          console.log(`分析字段映射: ${source} -> ${target}`);
          
          // 分析字段级关系
          const fieldMappings = this.analyzeFieldMappingsForTables(statement, source, target, index);
          console.log(`找到 ${fieldMappings.length} 个字段映射`);
          
          this.addRelationship({
            type: 'table',
            source: source,
            target: target,
            statement: index,
            columns: fieldMappings // 添加字段映射
          });
        });
      });
    } catch (error) {
      console.error('分析INSERT语句时出错:', error);
    }
  }

  /**
   * 分析SELECT语句
   */
  analyzeSelectStatement(statement, index) {
    const sourceTables = statement.tables || [];
    
    sourceTables.forEach(tableName => {
      this.addTable(tableName, {
        type: 'source',
        statement: index,
        sqlType: 'SELECT'
      });
    });
  }

  /**
   * 提取目标表
   */
  extractTargetTables(sql) {
    const tables = [];
    
    // INSERT INTO 或 INSERT OVERWRITE
    const insertPattern = /INSERT\s+(?:OVERWRITE\s+)?(?:INTO\s+)?(?:TABLE\s+)?([^\s\(]+)/i;
    const insertMatch = sql.match(insertPattern);
    if (insertMatch) {
      tables.push(this.normalizeTableName(insertMatch[1]));
    }

    // CREATE TABLE AS
    const createAsPattern = /CREATE\s+(?:EXTERNAL\s+)?TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?([^\s\(]+)\s+AS/i;
    const createAsMatch = sql.match(createAsPattern);
    if (createAsMatch) {
      tables.push(this.normalizeTableName(createAsMatch[1]));
    }

    return tables;
  }

  /**
   * 提取源表
   */
  extractSourceTables(sql) {
    const tables = new Set();
    
    try {
      console.log('开始提取源表，SQL:', sql.substring(0, 200) + '...');
      
             // FROM 子句 - 改进正则表达式以处理复杂表名（包括schema.table格式）
       const fromPattern = /FROM\s+([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)?(?:\s+[a-zA-Z_][a-zA-Z0-9_]*)?(?:\s*,\s*[a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)?(?:\s+[a-zA-Z_][a-zA-Z0-9_]*)?)*)/gi;
      let fromMatch;
      while ((fromMatch = fromPattern.exec(sql)) !== null) {
        console.log('FROM子句匹配:', fromMatch[1]);
        const tableNames = fromMatch[1].split(',');
        tableNames.forEach(name => {
          const cleanName = name.trim().split(/\s+/)[0]; // 取第一部分作为表名，忽略别名
          if (cleanName) {
            const normalizedName = this.normalizeTableName(cleanName);
            tables.add(normalizedName);
            console.log(`FROM子句找到表: ${cleanName} -> ${normalizedName}`);
          }
        });
      }

             // JOIN 子句 - 改进以处理复杂表名（包括schema.table格式）
       const joinPattern = /(?:INNER\s+|LEFT\s+|RIGHT\s+|FULL\s+)?JOIN\s+([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)?)(?:\s+([a-zA-Z_][a-zA-Z0-9_]*))?/gi;
      let joinMatch;
      while ((joinMatch = joinPattern.exec(sql)) !== null) {
        const tableName = joinMatch[1].trim();
        if (tableName) {
          const normalizedName = this.normalizeTableName(tableName);
          tables.add(normalizedName);
          console.log(`JOIN子句找到表: ${tableName} -> ${normalizedName}`);
        }
      }
      
      const result = Array.from(tables);
      console.log('源表提取完成，共找到:', result);
      return result;
      
    } catch (error) {
      console.error('提取源表时出错:', error);
      return [];
    }
  }

  /**
   * 从INSERT语句的SELECT部分提取源表字段信息
   */
  extractSourceTableFields(statement) {
    const sourceTableFields = {};
    
    try {
      console.log('开始提取源表字段信息...');
      
      // 首先建立别名映射关系
      const aliasMapping = this.extractTableAliases(statement.cleaned);
      console.log('表别名映射:', aliasMapping);
      
      // 提取SELECT子句
      const selectPattern = /SELECT\s+(.*?)\s+FROM/is;
      const selectMatch = statement.cleaned.match(selectPattern);
      
      if (!selectMatch) {
        console.warn('未找到SELECT子句');
        return sourceTableFields;
      }
      
      const selectClause = selectMatch[1];
      const fields = this.parseSelectFields(selectClause);
      
      // 收集所有被引用的字段
      const fieldReferences = new Set();
      
      fields.forEach(field => {
        if (field.dependencies && field.dependencies.length > 0) {
          field.dependencies.forEach(dep => {
            if (typeof dep === 'object') {
              // 新的对象格式
              if (dep.table && dep.field) {
                fieldReferences.add(`${dep.table}.${dep.field}`);
              } else if (dep.field) {
                // 如果没有表前缀，尝试推断可能的表
                fieldReferences.add(dep.field);
              } else if (dep.fullName) {
                fieldReferences.add(dep.fullName);
              }
            } else if (typeof dep === 'string') {
              // 兼容旧的字符串格式
              fieldReferences.add(dep);
            }
          });
        }
      });
      
      console.log('收集到的字段引用:', Array.from(fieldReferences));
      
             // 按表分组字段，考虑别名映射
       fieldReferences.forEach(ref => {
         if (ref.includes('.')) {
           const [tablePart, fieldPart] = ref.split('.');
           
           // 检查是否是别名，如果是则转换为真实表名
           let realTableName = tablePart;
           if (aliasMapping[tablePart]) {
             realTableName = aliasMapping[tablePart];
             console.log(`别名映射: ${tablePart} -> ${realTableName}`);
           }
           
           const normalizedTable = this.normalizeTableName(realTableName);
           
           console.log(`处理带表前缀的字段: ${tablePart}.${fieldPart} -> ${realTableName}.${fieldPart} (标准化: ${normalizedTable})`);
           
           if (!sourceTableFields[normalizedTable]) {
             sourceTableFields[normalizedTable] = [];
           }
           
           // 避免重复添加
           if (!sourceTableFields[normalizedTable].find(f => f.name === fieldPart)) {
             sourceTableFields[normalizedTable].push({
               name: fieldPart,
               type: 'unknown', // 类型待推断
               comment: ''
             });
             console.log(`为表 ${normalizedTable} 添加字段: ${fieldPart}`);
           }
         } else {
           // 对于没有表前缀的字段，尝试分配给所有可能的源表
           const sourceTables = this.extractSourceTables(statement.cleaned);
           console.log(`处理无表前缀字段 ${ref}，候选源表:`, sourceTables);
           
           sourceTables.forEach(table => {
             const normalizedTable = this.normalizeTableName(table);
             
             if (!sourceTableFields[normalizedTable]) {
               sourceTableFields[normalizedTable] = [];
             }
             
             // 避免重复添加
             if (!sourceTableFields[normalizedTable].find(f => f.name === ref)) {
               sourceTableFields[normalizedTable].push({
                 name: ref,
                 type: 'unknown',
                 comment: ''
               });
               console.log(`为表 ${normalizedTable} 添加无前缀字段: ${ref}`);
             }
           });
         }
       });
      
      // 打印结果
      Object.entries(sourceTableFields).forEach(([table, fields]) => {
        console.log(`表 ${table} 的字段:`, fields.map(f => f.name));
      });
      
    } catch (error) {
      console.error('提取源表字段信息时出错:', error);
    }
    
    return sourceTableFields;
  }

  /**
   * 提取表别名映射关系
   */
  extractTableAliases(sql) {
    const aliasMapping = {};
    
    try {
      // 匹配FROM子句中的表别名 - 支持 table alias 和 table as alias 格式
      const fromPattern = /FROM\s+([a-zA-Z_][a-zA-Z0-9_.]*)\s+(?:AS\s+)?([a-zA-Z_][a-zA-Z0-9_]*)/gi;
      let fromMatch;
      while ((fromMatch = fromPattern.exec(sql)) !== null) {
        const tableName = fromMatch[1].trim();
        const alias = fromMatch[2].trim();
        aliasMapping[alias] = tableName;
        console.log(`FROM别名: ${alias} -> ${tableName}`);
      }
      
      // 匹配JOIN子句中的表别名
      const joinPattern = /(?:INNER\s+|LEFT\s+|RIGHT\s+|FULL\s+)?JOIN\s+([a-zA-Z_][a-zA-Z0-9_.]*)\s+(?:AS\s+)?([a-zA-Z_][a-zA-Z0-9_]*)/gi;
      let joinMatch;
      while ((joinMatch = joinPattern.exec(sql)) !== null) {
        const tableName = joinMatch[1].trim();
        const alias = joinMatch[2].trim();
        aliasMapping[alias] = tableName;
        console.log(`JOIN别名: ${alias} -> ${tableName}`);
      }
      
    } catch (error) {
      console.error('提取表别名时出错:', error);
    }
    
    return aliasMapping;
  }

  /**
   * 分析特定表之间的字段映射关系
   */
  analyzeFieldMappingsForTables(statement, sourceTable, targetTable, statementIndex) {
    const sql = statement.cleaned;
    const fieldMappings = [];
    
    try {
      console.log(`分析字段映射: ${sourceTable} -> ${targetTable}`);
      
      // 获取表别名映射
      const aliasMapping = this.extractTableAliases(sql);
      
      // 提取SELECT子句中的字段
      const selectPattern = /SELECT\s+(.*?)\s+FROM/is;
      const selectMatch = sql.match(selectPattern);
      
      if (!selectMatch) {
        console.warn('未找到SELECT子句');
        return fieldMappings;
      }
      
      const selectClause = selectMatch[1];
      console.log('SELECT子句:', selectClause.substring(0, 200) + '...');
      
      const fields = this.parseSelectFields(selectClause);
      console.log(`解析到 ${fields.length} 个SELECT字段`);
      
      fields.forEach((field, index) => {
        const targetField = field.alias || field.name || `field_${index}`;
        console.log(`处理字段 ${index + 1}: ${field.expression} -> ${targetField}`);
        
        // 为每个依赖字段创建映射
        if (field.dependencies && field.dependencies.length > 0) {
          console.log(`字段 ${targetField} 有 ${field.dependencies.length} 个依赖`);
          field.dependencies.forEach(dep => {
            // 解析真实的源表名（考虑别名）
            let realSourceTable = dep.table || sourceTable;
            if (dep.table && aliasMapping[dep.table]) {
              realSourceTable = aliasMapping[dep.table];
              console.log(`字段映射别名解析: ${dep.table} -> ${realSourceTable}`);
            }
            
            fieldMappings.push({
              source: dep.field,
              target: targetField,
              expression: field.expression,
              type: field.type || 'column',
              sourceTable: realSourceTable,
              dependency: dep
            });
            
            // 同时记录到全局字段映射
            this.fieldMappings.push({
              sourceField: dep.field,
              targetField: targetField,
              sourceTable: realSourceTable,
              targetTable: targetTable,
              statement: statementIndex,
              type: field.type || 'column',
              expression: field.expression,
              dependency: dep
            });
            
            console.log(`创建映射: ${realSourceTable}.${dep.field} -> ${targetTable}.${targetField}`);
          });
        } else {
          // 如果没有找到依赖，使用传统方式
          const sourceField = field.name || field.expression.split('.').pop() || `field_${index}`;
          console.log(`使用传统方式映射: ${sourceField} -> ${targetField}`);
          
          fieldMappings.push({
            source: sourceField,
            target: targetField,
            expression: field.expression,
            type: field.type || 'column'
          });
          
          this.fieldMappings.push({
            sourceField: sourceField,
            targetField: targetField,
            sourceTable: sourceTable,
            targetTable: targetTable,
            statement: statementIndex,
            type: field.type || 'column',
            expression: field.expression
          });
        }
      });
      
      console.log(`总共创建了 ${fieldMappings.length} 个字段映射`);
      
    } catch (error) {
      console.error('分析字段映射时出错:', error);
    }
    
    return fieldMappings;
  }

  /**
   * 解析SELECT字段
   */
  parseSelectFields(selectClause) {
    const fields = [];
    
    try {
      console.log('开始解析SELECT字段:', selectClause.substring(0, 100) + '...');
      
      const fieldParts = this.splitSelectFields(selectClause);
      console.log(`分割成 ${fieldParts.length} 个字段部分`);
      
      fieldParts.forEach((part, index) => {
        const trimmed = part.trim();
        if (!trimmed) return;
        
        console.log(`解析字段 ${index + 1}: ${trimmed.substring(0, 50)}...`);
        
        const field = {
          expression: trimmed,
          name: '',
          alias: '',
          table: '',
          type: 'column',
          dependencies: [] // 新增：字段依赖列表
        };
        
        // 检查是否有别名 (AS关键字)
        const aliasPattern = /^(.+?)\s+AS\s+(\w+)$/i;
        const aliasMatch = trimmed.match(aliasPattern);
        
        if (aliasMatch) {
          field.expression = aliasMatch[1].trim();
          field.alias = aliasMatch[2];
          console.log(`找到AS别名: ${field.alias}`);
        } else {
          // 检查是否有隐式别名（表达式 别名）
          const implicitAliasPattern = /^(.+?)\s+(\w+)$/;
          const implicitMatch = trimmed.match(implicitAliasPattern);
          
          if (implicitMatch && !this.isKeyword(implicitMatch[2])) {
            field.expression = implicitMatch[1].trim();
            field.alias = implicitMatch[2];
            console.log(`找到隐式别名: ${field.alias}`);
          }
        }
        
        // 分析表达式中的字段依赖
        const expr = field.expression || trimmed;
        field.dependencies = this.extractFieldDependencies(expr);
        
        // 从表达式中提取主要字段名
        if (expr.includes('.')) {
          const directFieldMatch = expr.match(/(\w+)\.(\w+)/);
          if (directFieldMatch) {
            field.table = directFieldMatch[1];
            field.name = directFieldMatch[2];
            console.log(`提取表.字段: ${field.table}.${field.name}`);
          }
        } else {
          // 简单字段名或函数
          if (this.isFunction(expr)) {
            field.type = 'function';
            field.name = field.alias || this.extractFunctionName(expr);
            console.log(`识别为函数: ${field.name}`);
          } else if (expr === '*') {
            field.type = 'wildcard';
            field.name = '*';
            console.log('识别为通配符');
          } else {
            field.name = expr;
            console.log(`简单字段名: ${field.name}`);
          }
        }
        
        fields.push(field);
        console.log(`字段解析完成: ${field.alias || field.name}, 依赖数: ${field.dependencies.length}`);
      });
      
      console.log(`SELECT字段解析完成，共 ${fields.length} 个字段`);
      
    } catch (error) {
      console.error('解析SELECT字段时出错:', error);
    }
    
    return fields;
  }

  /**
   * 提取表达式中的字段依赖
   */
  extractFieldDependencies(expression) {
    const dependencies = [];
    
    try {
      console.log('分析表达式依赖:', expression);
      
      // 首先匹配所有的 table.field 模式（包括反引号和schema.table.field格式）
      const tableFieldPattern = /([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)?)\.\s*[`]?([a-zA-Z_][a-zA-Z0-9_]*)[`]?/g;
      let match;
      
      while ((match = tableFieldPattern.exec(expression)) !== null) {
        const table = match[1];
        const field = match[2];
        
        // 排除SQL关键字和函数名
        if (!this.isKeyword(table.toUpperCase()) && !this.isKeyword(field.toUpperCase()) && 
            !this.isCommonFunction(table.toUpperCase())) {
          dependencies.push({
            table: table,
            field: field,
            fullName: `${table}.${field}`
          });
          console.log(`找到字段依赖: ${table}.${field}`);
        }
      }
      
      // 重置正则表达式的lastIndex
      tableFieldPattern.lastIndex = 0;
      
      // 如果没有找到表.字段模式，尝试提取单独的字段名
      if (dependencies.length === 0) {
        // 对于复杂表达式，尝试提取所有可能的字段名
        const fieldPattern = /\b([a-zA-Z_][a-zA-Z0-9_]*)\b/g;
        const potentialFields = new Set();
        
        while ((match = fieldPattern.exec(expression)) !== null) {
          const fieldName = match[1];
          
          // 排除SQL关键字、函数名和常见的数值
          if (!this.isKeyword(fieldName.toUpperCase()) && 
              !this.isCommonFunction(fieldName.toUpperCase()) &&
              !this.isLiteral(fieldName)) {
            potentialFields.add(fieldName);
          }
        }
        
        // 对于复杂表达式，添加所有可能的字段
        if (potentialFields.size > 0) {
          potentialFields.forEach(fieldName => {
            dependencies.push({
              table: '',
              field: fieldName,
              fullName: fieldName
            });
            console.log(`找到字段依赖: ${fieldName}`);
          });
        }
      }
      
      console.log(`表达式 "${expression}" 共找到 ${dependencies.length} 个依赖`);
      
    } catch (error) {
      console.error('提取字段依赖时出错:', error);
    }
    
    return dependencies;
  }

  /**
   * 检查是否是常见的SQL函数
   */
  isCommonFunction(word) {
    const functions = [
      'COUNT', 'SUM', 'AVG', 'MIN', 'MAX', 'FIRST_VALUE', 'LAST_VALUE',
      'DENSE_RANK', 'ROW_NUMBER', 'RANK', 'LEAD', 'LAG',
      'DATE', 'YEAR', 'MONTH', 'DAY', 'HOUR', 'MINUTE', 'SECOND',
      'UPPER', 'LOWER', 'TRIM', 'SUBSTR', 'SUBSTRING', 'LENGTH',
      'CASE', 'WHEN', 'THEN', 'ELSE', 'END', 'IF', 'COALESCE', 'ISNULL',
      'CAST', 'CONVERT', 'DISTINCT', 'CONCAT', 'CURRENT_TIMESTAMP',
      'XXHASH', 'SHARED_UDF_PROD', 'CLUSTER', 'OVER', 'PARTITION'
    ];
    return functions.includes(word);
  }

  /**
   * 检查是否是字面值
   */
  isLiteral(word) {
    // 检查是否是数字
    if (/^\d+$/.test(word)) return true;
    
    // 检查是否是常见的字面值
    const literals = ['NULL', 'TRUE', 'FALSE', 'UNKNOWN'];
    return literals.includes(word.toUpperCase());
  }

  /**
   * 分割SELECT字段，正确处理嵌套函数和括号
   */
  splitSelectFields(selectClause) {
    const fields = [];
    let current = '';
    let parenCount = 0;
    let inString = false;
    let stringChar = '';
    
    for (let i = 0; i < selectClause.length; i++) {
      const char = selectClause[i];
      
      if (!inString && (char === '"' || char === "'")) {
        inString = true;
        stringChar = char;
      } else if (inString && char === stringChar) {
        inString = false;
        stringChar = '';
      } else if (!inString) {
        if (char === '(') {
          parenCount++;
        } else if (char === ')') {
          parenCount--;
        } else if (char === ',' && parenCount === 0) {
          fields.push(current.trim());
          current = '';
          continue;
        }
      }
      
      current += char;
    }
    
    if (current.trim()) {
      fields.push(current.trim());
    }
    
    return fields;
  }

  /**
   * 提取函数名
   */
  extractFunctionName(expr) {
    const match = expr.match(/(\w+)\s*\(/);
    return match ? match[1].toLowerCase() : 'function';
  }

  /**
   * 检查是否是SQL关键字
   */
  isKeyword(word) {
    const keywords = ['FROM', 'WHERE', 'GROUP', 'ORDER', 'HAVING', 'LIMIT', 'JOIN', 'ON'];
    return keywords.includes(word.toUpperCase());
  }

  /**
   * 检查是否是函数调用
   */
  isFunction(expression) {
    return /\w+\s*\(/.test(expression);
  }

  /**
   * 添加表信息
   */
  addTable(tableName, info) {
    if (!tableName) return;
    
    const normalizedName = this.normalizeTableName(tableName);
    
    if (this.tables.has(normalizedName)) {
      // 合并信息
      const existing = this.tables.get(normalizedName);
      existing.statements = existing.statements || [];
      existing.statements.push(info.statement);
      
      // 更新类型（优先级：target > stage > source）
      if (info.type === 'target' || 
          (info.type === 'stage' && existing.type === 'source')) {
        existing.type = info.type;
      }
      
      // 合并字段信息
      if (info.columns && info.columns.length > 0) {
        existing.columns = existing.columns || [];
        
        // 添加新字段，避免重复
        info.columns.forEach(newColumn => {
          const existingColumn = existing.columns.find(col => col.name === newColumn.name);
          if (!existingColumn) {
            existing.columns.push(newColumn);
            console.log(`为表 ${normalizedName} 添加字段: ${newColumn.name}`);
          } else {
            // 如果字段已存在，但类型是unknown，则更新类型
            if (existingColumn.type === 'unknown' && newColumn.type !== 'unknown') {
              existingColumn.type = newColumn.type;
              console.log(`更新表 ${normalizedName} 字段 ${newColumn.name} 的类型: ${newColumn.type}`);
            }
          }
        });
        
        console.log(`表 ${normalizedName} 现在有 ${existing.columns.length} 个字段`);
      }
    } else {
      this.tables.set(normalizedName, {
        table: normalizedName,
        ...info,
        statements: [info.statement],
        columns: info.columns || []
      });
      
      if (info.columns && info.columns.length > 0) {
        console.log(`新建表 ${normalizedName}，包含 ${info.columns.length} 个字段`);
      }
    }
  }

  /**
   * 添加关系
   */
  addRelationship(relationship) {
    if (!relationship.source || !relationship.target) return;
    
    const normalizedRel = {
      ...relationship,
      source: this.normalizeTableName(relationship.source),
      target: this.normalizeTableName(relationship.target)
    };
    
    // 避免重复关系
    const exists = this.relationships.some(rel => 
      rel.source === normalizedRel.source && 
      rel.target === normalizedRel.target &&
      rel.type === normalizedRel.type
    );
    
    if (!exists) {
      this.relationships.push(normalizedRel);
    }
  }

  /**
   * 标准化表名（使用统一的逻辑）
   */
  normalizeTableName(tableName) {
    if (!tableName) return '';
    
    // 移除别名
    const parts = tableName.split(/\s+/);
    tableName = parts[0];
    
    // 移除反引号、方括号、引号等
    tableName = tableName.replace(/[`\[\]"']/g, '');
    
    // 处理数据库.表名格式
    if (tableName.includes('.')) {
      const [database, table] = tableName.split('.');
      const result = `${database.toLowerCase()}.${table.toLowerCase()}`;
      console.log(`表名标准化: ${arguments[0]} -> ${result} (带数据库)`);
      return result;
    }
    
    const result = tableName.toLowerCase();
    console.log(`表名标准化: ${arguments[0]} -> ${result}`);
    return result;
  }

  /**
   * 获取分析结果
   */
  getResult() {
    const result = {
      tables: Object.fromEntries(this.tables),
      relationships: this.relationships,
      fieldMappings: this.fieldMappings,
      summary: {
        totalTables: this.tables.size,
        totalRelationships: this.relationships.length,
        totalFieldMappings: this.fieldMappings.length,
        sourceTables: Array.from(this.tables.values()).filter(t => t.type === 'source').length,
        targetTables: Array.from(this.tables.values()).filter(t => t.type === 'target').length,
        stageTables: Array.from(this.tables.values()).filter(t => t.type === 'stage').length
      }
    };
    
    // 调试输出：检查每个表的字段信息
    console.log('=== 分析结果 ===');
    Object.entries(result.tables).forEach(([name, table]) => {
      console.log(`表 ${name}: 类型=${table.type}, 字段数=${table.columns ? table.columns.length : 0}`);
      if (table.columns && table.columns.length > 0) {
        console.log(`  字段列表:`, table.columns.map(c => `${c.name}:${c.type}`).join(', '));
      }
    });
    console.log(`总字段映射数: ${result.fieldMappings.length}`);
    console.log('===============');
    
    return result;
  }

  /**
   * 生成血缘关系图数据
   */
  generateGraphData() {
    const result = this.getResult();
    
    // 转换为图形数据格式
    const nodes = Array.from(this.tables.values()).map(table => ({
      id: table.table,
      name: table.table,
      type: table.type,
      data: table
    }));
    
    const edges = this.relationships.map(rel => ({
      source: rel.source,
      target: rel.target,
      type: rel.type,
      data: rel
    }));
    
    return {
      nodes,
      edges,
      ...result
    };
  }

  /**
   * 分析血缘关系 - App.vue中调用的主方法
   */
  analyzeLineage(sqlContent) {
    if (!sqlContent) {
      return {};
    }

    // 直接使用已经创建的SQL解析器实例
    // 这里假设在App.vue中已经有sqlParser实例可用
    // 或者我们需要在这里重新创建一个简单的解析
    
    try {
      // 简单的SQL分割和解析
      const statements = this.splitSqlStatements(sqlContent);
      const parsedStatements = statements.map(stmt => this.parseSimpleStatement(stmt));
      
      // 分析血缘关系
      return this.analyze(parsedStatements);
    } catch (error) {
      console.error('Error analyzing lineage:', error);
      return {};
    }
  }

  /**
   * 简单的SQL语句分割
   */
  splitSqlStatements(sql) {
    if (!sql || typeof sql !== 'string') return [];
    
    const statements = [];
    let current = '';
    let inString = false;
    let stringChar = '';
    
    for (let i = 0; i < sql.length; i++) {
      const char = sql[i];
      
      if (!inString && (char === "'" || char === '"')) {
        inString = true;
        stringChar = char;
      } else if (inString && char === stringChar) {
        if (i > 0 && sql[i - 1] !== '\\') {
          inString = false;
          stringChar = '';
        }
      } else if (!inString && char === ';') {
        const trimmed = current.trim();
        if (trimmed) {
          statements.push(trimmed);
        }
        current = '';
        continue;
      }
      
      current += char;
    }
    
    const trimmed = current.trim();
    if (trimmed) {
      statements.push(trimmed);
    }
    
    return statements.filter(stmt => stmt.length > 0);
  }

  /**
   * 简单的语句解析
   */
  parseSimpleStatement(sql) {
    const cleanedSql = sql.replace(/--.*$/gm, '').replace(/\/\*[\s\S]*?\*\//g, '').replace(/\s+/g, ' ').trim();
    const upperSql = cleanedSql.toUpperCase();
    
    let type = 'UNKNOWN';
    if (upperSql.startsWith('SELECT')) type = 'SELECT';
    else if (upperSql.startsWith('INSERT')) type = 'INSERT';
    else if (upperSql.startsWith('CREATE')) type = 'CREATE';
    
    return {
      type,
      original: sql,
      cleaned: cleanedSql,
      tables: this.extractTablesFromSql(cleanedSql),
      columns: []
    };
  }

  /**
   * 从SQL中提取表名
   */
  extractTablesFromSql(sql) {
    const tables = new Set();
    
    // 提取FROM子句中的表
    const fromPattern = /FROM\s+([^\s,\(]+)/gi;
    let fromMatch;
    while ((fromMatch = fromPattern.exec(sql)) !== null) {
      const tableName = fromMatch[1].trim();
      if (tableName) {
        tables.add(this.normalizeTableName(tableName));
      }
    }
    
    // 提取JOIN子句中的表
    const joinPattern = /JOIN\s+([^\s\(]+)/gi;
    let joinMatch;
    while ((joinMatch = joinPattern.exec(sql)) !== null) {
      const tableName = joinMatch[1].trim();
      if (tableName) {
        tables.add(this.normalizeTableName(tableName));
      }
    }
    
    // 提取INSERT INTO中的表
    const insertPattern = /INSERT\s+(?:OVERWRITE\s+)?(?:INTO\s+)?(?:TABLE\s+)?([^\s\(]+)/i;
    const insertMatch = sql.match(insertPattern);
    if (insertMatch) {
      const tableName = insertMatch[1].trim();
      if (tableName) {
        tables.add(this.normalizeTableName(tableName));
      }
    }
    
    // 提取CREATE TABLE中的表
    const createPattern = /CREATE\s+(?:EXTERNAL\s+)?TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?([^\s\(]+)/i;
    const createMatch = sql.match(createPattern);
    if (createMatch) {
      const tableName = createMatch[1].trim();
      if (tableName) {
        tables.add(this.normalizeTableName(tableName));
      }
    }
    
    return Array.from(tables);
  }



  /**
   * 设置表结构信息
   */
  setTableSchemas(schemas) {
    this.tableSchemas = schemas || {};
    
    // 将表结构信息合并到已分析的表中
    for (const [tableName, schema] of Object.entries(this.tableSchemas)) {
      if (this.tables.has(tableName) && schema) {
        const tableInfo = this.tables.get(tableName);
        tableInfo.columns = schema.columns || [];
        tableInfo.database = schema.database || tableInfo.database;
      }
    }
  }
} 