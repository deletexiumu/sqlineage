import axios from 'axios'

const API_BASE_URL = 'http://localhost:8000/api'

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor to add auth token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('authToken')
    if (token) {
      config.headers.Authorization = `Token ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor for handling errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('authToken')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export interface HiveTable {
  id: number
  name: string
  database: string
  columns: Array<{
    name: string
    type: string
    comment: string
  }>
  full_name: string
  created_at: string
  updated_at: string
}

export interface GitRepo {
  id: number
  name: string
  repo_url: string
  username: string
  auth_type: string
  access_mode: string
  branch: string
  ssl_verify: boolean
  is_active: boolean
  created_at: string
  updated_at: string
  last_sync: string | null
}

export interface LineageRelation {
  id: number
  source_table: HiveTable
  target_table: HiveTable
  sql_script_path: string
  relation_type: string
  process_id: string
  created_at: string
}

export interface LineageParseJob {
  id: number
  git_repo: number
  git_repo_name: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  total_files: number
  processed_files: number
  failed_files: number
  progress_percentage: number
  error_message: string
  started_at: string | null
  completed_at: string | null
  created_at: string
}

// Auth API
export const authAPI = {
  login: (username: string, password: string) =>
    api.post('/auth/login/', { username, password }),
}

// Metadata API
export const metadataAPI = {
  getTables: (params?: { database?: string; search?: string }) =>
    api.get<HiveTable[]>('/metadata/tables/', { params }),
  
  getTable: (id: number) =>
    api.get<HiveTable>(`/metadata/tables/${id}/`),
  
  getDatabases: () =>
    api.get<string[]>('/metadata/tables/databases/'),
  
  getAutocomplete: (query: string, limit = 10, extraParams = {}) =>
    api.get('/metadata/tables/autocomplete/', { params: { query, limit, ...extraParams } }),
  
  getStatistics: () =>
    api.get('/metadata/tables/statistics/'),
  
  getBusinessMappings: () =>
    api.get('/metadata/business-mappings/'),
  
  createBusinessMapping: (data: any) =>
    api.post('/metadata/business-mappings/', data),
  
  // 元数据导入
  importMetadata: (formData: FormData) =>
    api.post('/metadata/import/import_metadata/', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    }),
  
  previewImport: (formData: FormData) =>
    api.post('/metadata/import/import_metadata/', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    }),
  
  getImportTemplate: (format: string) => {
    // 根据格式设置不同的响应类型
    if (format === 'excel') {
      return api.get(`/metadata/import/get_template/?format=${format}`, {
        responseType: 'blob'
      })
    } else {
      // CSV和JSON返回文本内容
      return api.get(`/metadata/import/get_template/?format=${format}`, {
        responseType: 'text'
      })
    }
  },
  
  // Hive连接管理
  testHiveConnection: (config: any) =>
    api.post('/metadata/hive-connection/test_connection/', config),
  
  getHiveDatabases: (config: any) =>
    api.post('/metadata/hive-connection/get_databases/', config),
  
  getHiveTables: (config: any, database: string) =>
    api.post('/metadata/hive-connection/get_tables/', { ...config, database }),
  
  getHiveDatabaseTree: (config: any) =>
    api.post('/metadata/hive-connection/get_database_tree/', config),
  
  selectiveHiveSync: (data: any) =>
    api.post('/metadata/hive-connection/selective_sync/', data),
  
  // 元数据删除功能
  clearAllMetadata: () =>
    api.delete('/metadata/tables/clear_all/'),
  
  deleteDatabase: (database: string) =>
    api.delete('/metadata/tables/delete_database/', { params: { database } }),
  
  deleteTable: (database: string, table: string) =>
    api.delete('/metadata/tables/delete_table/', { params: { database, table } }),
}

// Git API
export const gitAPI = {
  getRepos: () =>
    api.get<GitRepo[]>('/git/repos/'),
  
  createRepo: (data: Partial<GitRepo> & { password: string }) =>
    api.post<GitRepo>('/git/repos/', data),
  
  updateRepo: (id: number, data: Partial<GitRepo> & { password?: string }) =>
    api.patch<GitRepo>(`/git/repos/${id}/`, data),
  
  deleteRepo: (id: number) =>
    api.delete(`/git/repos/${id}/`),
  
  syncRepo: (id: number) =>
    api.post(`/git/repos/${id}/sync/`),
  
  forceReclone: (id: number) =>
    api.post(`/git/repos/${id}/force_reclone/`),
  
  getRepoFiles: (id: number) =>
    api.get(`/git/repos/${id}/files/`),
  
  readFile: (id: number, filePath: string) =>
    api.post(`/git/repos/${id}/read_file/`, { file_path: filePath }),
  
  writeFile: (id: number, filePath: string, content: string) =>
    api.post(`/git/repos/${id}/write_file/`, { file_path: filePath, content }),
  
  commitFiles: (id: number, filePaths: string[], commitMessage: string) =>
    api.post(`/git/repos/${id}/commit/`, { file_paths: filePaths, commit_message: commitMessage }),
  
  getCommits: (id: number, limit = 10) =>
    api.get(`/git/repos/${id}/commits/`, { params: { limit } }),
  
  getBranches: (id: number) =>
    api.get(`/git/repos/${id}/branches/`),
  
  switchBranch: (id: number, branch: string) =>
    api.post(`/git/repos/${id}/switch_branch/`, { branch }),
}

// Lineage API
export const lineageAPI = {
  getRelations: (params?: { source_table?: string; target_table?: string }) =>
    api.get<LineageRelation[]>('/lineage/relations/', { params }),
  
  parseSQL: (sqlText: string, filePath = '') =>
    api.post('/lineage/relations/parse_sql/', { sql_text: sqlText, file_path: filePath }),
  
  parseRepo: (repoId: number) =>
    api.post('/lineage/relations/parse_repo/', { repo_id: repoId }),
  
  getImpact: (tableName: string) =>
    api.get('/lineage/relations/impact/', { params: { table_name: tableName } }),
  
  getGraph: (tableName: string, depth = 2) =>
    api.get('/lineage/relations/graph/', { params: { table_name: tableName, depth } }),
  
  getJobs: () =>
    api.get<LineageParseJob[]>('/lineage/jobs/'),
  
  getJob: (id: number) =>
    api.get<LineageParseJob>(`/lineage/jobs/${id}/`),
}

export default api