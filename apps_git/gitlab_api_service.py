"""
GitLab API 服务 - 纯API方式操作Git仓库
不依赖本地clone，直接通过API获取文件和分支信息
"""
import requests
import logging
from urllib.parse import urlparse, quote
from typing import List, Dict, Optional, Any
import base64

logger = logging.getLogger(__name__)


class GitLabAPIService:
    """GitLab API服务类"""
    
    def __init__(self, repo_url: str, token: str, ssl_verify: bool = True):
        """
        初始化GitLab API服务
        
        Args:
            repo_url: Git仓库URL
            token: Personal Access Token
            ssl_verify: 是否验证SSL证书
        """
        self.repo_url = repo_url
        self.token = token
        self.ssl_verify = ssl_verify
        self.base_url, self.project_path = self._parse_repo_url(repo_url)
        self.project_id = None
        
        # 设置请求会话
        self.session = requests.Session()
        self.session.headers.update({
            'Private-Token': token,
            'Content-Type': 'application/json'
        })
        self.session.verify = ssl_verify
        
        # 获取项目ID
        self._get_project_id()
    
    def _parse_repo_url(self, repo_url: str) -> tuple:
        """解析仓库URL，提取基础URL和项目路径"""
        parsed = urlparse(repo_url)
        
        # 构建API基础URL
        base_url = f"{parsed.scheme}://{parsed.netloc}/api/v4"
        
        # 提取项目路径 (移除.git后缀)
        project_path = parsed.path.strip('/').replace('.git', '')
        
        return base_url, project_path
    
    def _get_project_id(self):
        """获取项目ID"""
        try:
            # URL编码项目路径
            encoded_path = quote(self.project_path, safe='')
            url = f"{self.base_url}/projects/{encoded_path}"
            
            response = self.session.get(url)
            response.raise_for_status()
            
            project_data = response.json()
            self.project_id = project_data['id']
            logger.info(f"Found project ID: {self.project_id} for {self.project_path}")
            
        except Exception as e:
            logger.error(f"Failed to get project ID for {self.project_path}: {str(e)}")
            raise Exception(f"无法获取项目信息: {str(e)}")
    
    def get_branches(self) -> List[str]:
        """获取所有分支列表"""
        try:
            url = f"{self.base_url}/projects/{self.project_id}/repository/branches"
            
            response = self.session.get(url)
            response.raise_for_status()
            
            branches_data = response.json()
            branches = [branch['name'] for branch in branches_data]
            
            logger.info(f"Found {len(branches)} branches for project {self.project_id}")
            return branches
            
        except Exception as e:
            logger.error(f"Failed to get branches: {str(e)}")
            return ['main', 'master']  # 返回默认分支
    
    def get_file_tree(self, branch: str = 'main', path: str = '', recursive: bool = True) -> List[Dict]:
        """
        获取指定分支和路径下的文件树
        
        Args:
            branch: 分支名
            path: 路径（空字符串表示根目录）
            recursive: 是否递归获取子目录
            
        Returns:
            文件和目录信息列表
        """
        try:
            url = f"{self.base_url}/projects/{self.project_id}/repository/tree"
            params = {
                'ref': branch,
                'path': path,
                'recursive': recursive,
                'per_page': 100  # 每页最多100个文件
            }
            
            all_files = []
            page = 1
            
            while True:
                params['page'] = page
                response = self.session.get(url, params=params)
                response.raise_for_status()
                
                files_data = response.json()
                if not files_data:
                    break
                
                # 过滤出SQL文件
                sql_files = [
                    {
                        'path': file['path'],
                        'name': file['name'],
                        'type': file['type'],  # 'blob' for files, 'tree' for directories
                        'size': file.get('size', 0),
                        'id': file['id']
                    }
                    for file in files_data
                    if file['type'] == 'blob' and file['name'].lower().endswith('.sql')
                ]
                
                all_files.extend(sql_files)
                
                # 检查是否还有更多页
                if len(files_data) < params['per_page']:
                    break
                page += 1
            
            logger.info(f"Found {len(all_files)} SQL files in branch {branch}")
            return all_files
            
        except Exception as e:
            logger.error(f"Failed to get file tree: {str(e)}")
            return []
    
    def get_file_content(self, file_path: str, branch: str = 'main') -> Optional[str]:
        """
        获取指定文件的内容
        
        Args:
            file_path: 文件路径
            branch: 分支名
            
        Returns:
            文件内容字符串，失败时返回None
        """
        try:
            # URL编码文件路径
            encoded_path = quote(file_path, safe='/')
            url = f"{self.base_url}/projects/{self.project_id}/repository/files/{encoded_path}"
            
            params = {'ref': branch}
            response = self.session.get(url, params=params)
            response.raise_for_status()
            
            file_data = response.json()
            
            # 解码文件内容
            if file_data.get('encoding') == 'base64':
                content = base64.b64decode(file_data['content']).decode('utf-8')
            else:
                content = file_data['content']
            
            logger.debug(f"Retrieved file content for {file_path} ({len(content)} chars)")
            return content
            
        except Exception as e:
            logger.error(f"Failed to get file content for {file_path}: {str(e)}")
            return None
    
    def get_file_info(self, file_path: str, branch: str = 'main') -> Optional[Dict]:
        """
        获取文件信息（不包含内容）
        
        Args:
            file_path: 文件路径
            branch: 分支名
            
        Returns:
            文件信息字典
        """
        try:
            encoded_path = quote(file_path, safe='/')
            url = f"{self.base_url}/projects/{self.project_id}/repository/files/{encoded_path}"
            
            params = {'ref': branch}
            response = self.session.get(url, params=params)
            response.raise_for_status()
            
            file_data = response.json()
            
            return {
                'path': file_data['file_path'],
                'name': file_data['file_name'],
                'size': file_data['size'],
                'encoding': file_data['encoding'],
                'commit_id': file_data['commit_id'],
                'last_commit_id': file_data['last_commit_id']
            }
            
        except Exception as e:
            logger.error(f"Failed to get file info for {file_path}: {str(e)}")
            return None
    
    def test_connection(self) -> bool:
        """测试连接是否成功"""
        try:
            url = f"{self.base_url}/projects/{self.project_id}"
            response = self.session.get(url)
            response.raise_for_status()
            
            logger.info(f"Connection test successful for project {self.project_id}")
            return True
            
        except Exception as e:
            logger.error(f"Connection test failed: {str(e)}")
            return False
    
    def get_project_info(self) -> Optional[Dict]:
        """获取项目基本信息"""
        try:
            url = f"{self.base_url}/projects/{self.project_id}"
            response = self.session.get(url)
            response.raise_for_status()
            
            project_data = response.json()
            
            return {
                'id': project_data['id'],
                'name': project_data['name'],
                'path': project_data['path'],
                'description': project_data.get('description', ''),
                'default_branch': project_data.get('default_branch', 'main'),
                'created_at': project_data['created_at'],
                'last_activity_at': project_data['last_activity_at']
            }
            
        except Exception as e:
            logger.error(f"Failed to get project info: {str(e)}")
            return None