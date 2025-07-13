import git
import os
import logging
import ssl
import urllib3
from pathlib import Path
from urllib.parse import urlparse, urlunparse
from .models import GitRepo
from .gitlab_api_service import GitLabAPIService
from django.utils import timezone

# 禁用urllib3的SSL警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


logger = logging.getLogger(__name__)


class GitService:
    def __init__(self, git_repo: GitRepo):
        self.git_repo = git_repo
        self.repo = None

    def _get_auth_url(self, auth_format=None):
        parsed = urlparse(self.git_repo.repo_url)
        password = self.git_repo.get_password()
        
        # 优先使用已验证成功的认证格式
        if auth_format is None and self.git_repo.successful_auth_format:
            auth_format = self.git_repo.successful_auth_format
            logger.info(f"Using previously successful auth format: {auth_format}")
        
        # 根据认证类型构建URL
        if self.git_repo.auth_type == 'token':
            # GitLab Token认证: 多种格式支持
            if auth_format == 'token_only':
                # 格式1: token作为用户名，密码留空
                auth_netloc = f"{password}:@{parsed.netloc}"
            elif auth_format == 'gitlab_ci_token':
                # 格式2: gitlab-ci-token + token作为密码
                auth_netloc = f"gitlab-ci-token:{password}@{parsed.netloc}"
            elif auth_format == 'username_token':
                # 格式3: 用设置的用户名 + token
                username = self.git_repo.username if self.git_repo.username else 'git'
                auth_netloc = f"{username}:{password}@{parsed.netloc}"
            elif auth_format == 'oauth2':
                # 格式4: oauth2格式
                auth_netloc = f"oauth2:{password}@{parsed.netloc}"
            else:
                # 默认格式（第一次尝试）
                auth_netloc = f"{password}:@{parsed.netloc}"
        else:
            # 用户名密码认证
            auth_netloc = f"{self.git_repo.username}:{password}@{parsed.netloc}"
        
        auth_url = urlunparse((
            parsed.scheme,
            auth_netloc,
            parsed.path,
            parsed.params,
            parsed.query,
            parsed.fragment
        ))
        
        logger.info(f"Using auth URL format '{auth_format}' for {self.git_repo.auth_type}: {parsed.scheme}://<credentials>@{parsed.netloc}{parsed.path}")
        return auth_url, auth_format or 'default'

    def _clear_git_credentials(self):
        """清理Git凭据缓存，解决Windows凭据管理器问题"""
        try:
            import platform
            if platform.system() == 'Windows':
                # 在Windows上，清理可能缓存的凭据
                parsed = urlparse(self.git_repo.repo_url)
                host = parsed.netloc
                
                # 尝试清理Windows凭据管理器中的Git凭据
                import subprocess
                try:
                    # 清理通用凭据
                    subprocess.run([
                        'cmdkey', '/delete:LegacyGeneric', f'target=git:http://{host}'
                    ], capture_output=True, timeout=10)
                    subprocess.run([
                        'cmdkey', '/delete:LegacyGeneric', f'target=git:https://{host}'
                    ], capture_output=True, timeout=10)
                    logger.info(f"Cleared Windows credentials for {host}")
                except (subprocess.TimeoutExpired, subprocess.SubprocessError):
                    pass  # 忽略清理失败
                    
            # 通用Git凭据清理
            if hasattr(self, 'repo') and self.repo:
                try:
                    # 禁用凭据助手
                    self.repo.git.config('credential.helper', '')
                    logger.info("Disabled Git credential helper")
                except:
                    pass
                    
        except Exception as e:
            logger.debug(f"Credential cleanup failed: {str(e)}")
    
    def _ensure_directory_permissions(self, path):
        """确保目录具有正确的权限，特别是Windows环境"""
        try:
            import platform
            import stat
            
            if platform.system() == 'Windows':
                # Windows下处理文件权限问题
                for root, dirs, files in os.walk(path):
                    # 设置目录权限
                    try:
                        os.chmod(root, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)
                    except PermissionError:
                        pass  # 忽略权限错误，继续处理
                    
                    # 设置文件权限
                    for file in files:
                        file_path = os.path.join(root, file)
                        try:
                            os.chmod(file_path, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH)
                        except PermissionError:
                            pass  # 忽略权限错误，继续处理
                            
            logger.debug(f"Ensured directory permissions for {path}")
            
        except Exception as e:
            logger.debug(f"Permission setup failed for {path}: {str(e)}")
            # 权限设置失败不应该中断主流程

    def clone_or_pull(self):
        local_path = self.git_repo.repo_local_path
        
        # 智能认证重试机制
        auth_formats_to_try = []
        
        if self.git_repo.auth_type == 'token':
            # 如果有成功的认证格式，优先使用
            if self.git_repo.successful_auth_format:
                auth_formats_to_try.append(self.git_repo.successful_auth_format)
            
            # 添加其他认证格式作为备选
            all_formats = ['token_only', 'gitlab_ci_token', 'username_token', 'oauth2']
            for fmt in all_formats:
                if fmt not in auth_formats_to_try:
                    auth_formats_to_try.append(fmt)
        else:
            # 密码认证只有一种格式
            auth_formats_to_try.append('default')
        
        # 尝试不同的认证格式
        for auth_format in auth_formats_to_try:
            try:
                success = self._attempt_clone_or_pull_with_auth(auth_format)
                if success:
                    # 记录成功的认证格式
                    if self.git_repo.successful_auth_format != auth_format:
                        self.git_repo.successful_auth_format = auth_format
                        self.git_repo.save()
                        logger.info(f"Recorded successful auth format: {auth_format}")
                    return True
            except Exception as e:
                logger.warning(f"Auth format '{auth_format}' failed: {str(e)}")
                continue
        
        logger.error(f"All authentication methods failed for {self.git_repo.name}")
        return False

    def _attempt_clone_or_pull_with_auth(self, auth_format):
        """使用指定的认证格式尝试克隆或拉取"""
        local_path = self.git_repo.repo_local_path
        auth_url, used_format = self._get_auth_url(auth_format)
        
        # 清理可能的凭据缓存问题
        self._clear_git_credentials()
        
        # 配置SSL验证选项
        env_vars = {}
        if not self.git_repo.ssl_verify:
            env_vars.update({
                'GIT_SSL_NO_VERIFY': '1',
                'GIT_CURL_VERBOSE': '0'
            })
            
        # 禁用凭据缓存，强制使用URL中的认证信息
        env_vars.update({
            'GIT_TERMINAL_PROMPT': '0',
            'GIT_ASKPASS': 'echo',
        })
        
        try:
            if os.path.exists(local_path):
                # 拉取现有仓库
                self._ensure_directory_permissions(local_path)
                self.repo = git.Repo(local_path)
                
                with self.repo.git.custom_environment(**env_vars):
                    self.repo.git.config('credential.helper', '')
                    self.repo.git.remote('set-url', 'origin', auth_url)
                    self.repo.git.fetch('origin')
                    self.repo.git.checkout('-B', self.git_repo.branch, f'origin/{self.git_repo.branch}')
            else:
                # 克隆新仓库
                os.makedirs(os.path.dirname(local_path), exist_ok=True)
                clone_env = dict(os.environ)
                clone_env.update(env_vars)
                
                self.repo = git.Repo.clone_from(
                    auth_url, 
                    local_path,
                    branch=self.git_repo.branch,
                    env=clone_env
                )
                
                self.repo.git.config('credential.helper', '')
                if not self.git_repo.ssl_verify:
                    self.repo.git.config('http.sslVerify', 'false')
            
            self.git_repo.last_sync = timezone.now()
            self.git_repo.save()
            return True
            
        except git.exc.GitCommandError as e:
            error_msg = str(e)
            if ('Authentication failed' in error_msg or 
                'access denied' in error_msg.lower() or 
                'HTTP Basic: Access denied' in error_msg):
                raise Exception(f"认证失败: {error_msg}")
            elif 'certificate verify failed' in error_msg:
                raise Exception("SSL证书验证失败")
            else:
                raise Exception(f"Git操作失败: {error_msg}")
        except Exception as e:
            raise Exception(f"仓库同步失败: {str(e)}")

    def get_sql_files(self):
        """获取SQL文件列表，支持clone和API两种模式"""
        
        if self.git_repo.access_mode == 'api':
            # API模式：直接通过GitLab API获取文件列表
            return self._get_sql_files_via_api()
        else:
            # Clone模式：使用原有的本地克隆方式
            return self._get_sql_files_via_clone()
    
    def _get_sql_files_via_api(self):
        """通过API方式获取SQL文件列表"""
        try:
            api_service = GitLabAPIService(
                repo_url=self.git_repo.repo_url,
                token=self.git_repo.get_password(),
                ssl_verify=self.git_repo.ssl_verify
            )
            
            files = api_service.get_file_tree(branch=self.git_repo.branch)
            
            # 转换为统一格式
            sql_files = []
            for file in files:
                sql_files.append({
                    'path': file['path'],
                    'full_path': file['path'],  # API模式下full_path就是相对路径
                    'size': file['size'],
                    'modified': None,  # API模式下暂不提供修改时间
                    'api_mode': True
                })
            
            sql_files.sort(key=lambda x: x['path'])
            logger.info(f"Found {len(sql_files)} SQL files via API for {self.git_repo.name}")
            return sql_files
            
        except Exception as e:
            logger.error(f"Failed to get SQL files via API from {self.git_repo.name}: {str(e)}")
            return []
    
    def _get_sql_files_via_clone(self):
        """通过本地克隆方式获取SQL文件列表"""
        if not self.repo or not os.path.exists(self.git_repo.repo_local_path):
            if not self.clone_or_pull():
                return []
        
        sql_files = []
        try:
            repo_path = Path(self.git_repo.repo_local_path)
            for sql_file in repo_path.rglob("*.sql"):
                if sql_file.is_file():
                    relative_path = sql_file.relative_to(repo_path)
                    sql_files.append({
                        'path': str(relative_path),
                        'full_path': str(sql_file),
                        'size': sql_file.stat().st_size,
                        'modified': sql_file.stat().st_mtime,
                        'api_mode': False
                    })
            
            sql_files.sort(key=lambda x: x['path'])
            return sql_files
            
        except Exception as e:
            logger.error(f"Failed to get SQL files from {self.git_repo.name}: {str(e)}")
            return []

    def read_file(self, file_path):
        """读取文件内容，支持clone和API两种模式"""
        
        if self.git_repo.access_mode == 'api':
            # API模式：直接通过GitLab API读取文件内容
            return self._read_file_via_api(file_path)
        else:
            # Clone模式：从本地克隆的文件读取
            return self._read_file_via_clone(file_path)
    
    def _read_file_via_api(self, file_path):
        """通过API方式读取文件内容"""
        try:
            api_service = GitLabAPIService(
                repo_url=self.git_repo.repo_url,
                token=self.git_repo.get_password(),
                ssl_verify=self.git_repo.ssl_verify
            )
            
            content = api_service.get_file_content(file_path, branch=self.git_repo.branch)
            if content is not None:
                logger.debug(f"Read file {file_path} via API ({len(content)} chars)")
            
            return content
            
        except Exception as e:
            logger.error(f"Failed to read file {file_path} via API from {self.git_repo.name}: {str(e)}")
            return None
    
    def _read_file_via_clone(self, file_path):
        """通过本地克隆方式读取文件内容"""
        if not self.repo or not os.path.exists(self.git_repo.repo_local_path):
            if not self.clone_or_pull():
                return None
        
        try:
            full_path = os.path.join(self.git_repo.repo_local_path, file_path)
            if not os.path.exists(full_path):
                return None
            
            with open(full_path, 'r', encoding='utf-8') as f:
                return f.read()
                
        except Exception as e:
            logger.error(f"Failed to read file {file_path} from {self.git_repo.name}: {str(e)}")
            return None

    def write_file(self, file_path, content):
        if not self.repo or not os.path.exists(self.git_repo.repo_local_path):
            if not self.clone_or_pull():
                return False
        
        try:
            full_path = os.path.join(self.git_repo.repo_local_path, file_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to write file {file_path} to {self.git_repo.name}: {str(e)}")
            return False

    def commit_and_push(self, file_paths, commit_message):
        if not self.repo:
            return False
        
        try:
            for file_path in file_paths:
                self.repo.index.add([file_path])
            
            self.repo.index.commit(commit_message)
            
            origin = self.repo.remotes.origin
            
            # 确保remote refspec正确设置
            try:
                origin.refs
            except (AttributeError, AssertionError):
                logger.info(f"Setting up remote refspec for push operation")
                self.repo.git.config('remote.origin.fetch', '+refs/heads/*:refs/heads/*')
            
            # 获取当前分支名
            try:
                current_branch = self.repo.active_branch.name
            except:
                current_branch = self.git_repo.branch
            
            # 推送到远程分支
            origin.push(refspec=f'{current_branch}:{current_branch}')
            
            logger.info(f"Successfully committed and pushed changes to {self.git_repo.name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to commit and push to {self.git_repo.name}: {str(e)}")
            return False

    def get_remote_branches(self):
        """获取远程仓库的分支列表，支持clone和API两种模式"""
        
        if self.git_repo.access_mode == 'api':
            # API模式：直接通过GitLab API获取分支列表
            return self._get_branches_via_api()
        else:
            # Clone模式：使用原有的Git命令方式
            return self._get_branches_via_clone()
    
    def _get_branches_via_api(self):
        """通过API方式获取分支列表"""
        try:
            api_service = GitLabAPIService(
                repo_url=self.git_repo.repo_url,
                token=self.git_repo.get_password(),
                ssl_verify=self.git_repo.ssl_verify
            )
            
            branches = api_service.get_branches()
            logger.info(f"Found {len(branches)} branches via API for {self.git_repo.name}")
            return branches
            
        except Exception as e:
            logger.error(f"Failed to get branches via API from {self.git_repo.name}: {str(e)}")
            return ['main', 'master']  # 返回默认分支
    
    def _get_branches_via_clone(self):
        """通过本地克隆方式获取分支列表"""
        local_path = self.git_repo.repo_local_path
        auth_url = self._get_auth_url()
        
        # 配置SSL验证选项
        env_vars = {}
        if not self.git_repo.ssl_verify:
            env_vars.update({
                'GIT_SSL_NO_VERIFY': '1',
                'GIT_CURL_VERBOSE': '0'
            })
        
        try:
            # 如果本地仓库不存在，临时clone来获取分支信息
            if not os.path.exists(local_path):
                temp_path = f"{local_path}_temp"
                try:
                    # 只获取远程引用，不下载完整仓库
                    clone_env = dict(os.environ)
                    clone_env.update(env_vars)
                    
                    temp_repo = git.Repo.clone_from(
                        auth_url,
                        temp_path,
                        no_checkout=True,  # 不检出文件
                        env=clone_env
                    )
                    
                    # 获取远程分支列表
                    remote_refs = temp_repo.git.ls_remote('--heads', 'origin').split('\n')
                    branches = []
                    for ref in remote_refs:
                        if ref.strip():
                            branch_name = ref.split('\t')[1].replace('refs/heads/', '')
                            branches.append(branch_name)
                    
                    # 清理临时目录
                    import shutil
                    shutil.rmtree(temp_path)
                    
                    return branches
                    
                except Exception as e:
                    logger.error(f"Failed to get remote branches: {str(e)}")
                    # 如果临时目录存在，清理它
                    if os.path.exists(temp_path):
                        import shutil
                        shutil.rmtree(temp_path)
                    return ['main', 'master']  # 返回常见默认分支
            else:
                # 使用现有仓库获取分支信息
                self.repo = git.Repo(local_path)
                with self.repo.git.custom_environment(**env_vars):
                    # 先fetch获取最新的远程分支信息
                    self.repo.git.config('remote.origin.fetch', '+refs/heads/*:refs/heads/*')
                    
                    try:
                        self.repo.git.fetch('origin')
                        
                        # 尝试使用ls-remote获取远程分支，这样更可靠
                        try:
                            remote_refs_output = self.repo.git.ls_remote('--heads', 'origin')
                            branches = []
                            for line in remote_refs_output.split('\n'):
                                if line.strip() and 'refs/heads/' in line:
                                    branch_name = line.split('refs/heads/')[-1].strip()
                                    branches.append(branch_name)
                            return branches
                        except git.exc.GitCommandError:
                            # 备选方案：使用branch -r
                            try:
                                remote_branches = self.repo.git.branch('-r').split('\n')
                                branches = [b.strip().replace('origin/', '') 
                                           for b in remote_branches 
                                           if 'origin/' in b and '->' not in b and b.strip()]
                                return branches
                            except git.exc.GitCommandError:
                                # 最后的备选方案
                                return ['main', 'master']
                    except git.exc.GitCommandError:
                        # 如果fetch失败，返回默认分支
                        return ['main', 'master']
                    
        except Exception as e:
            logger.error(f"Failed to get remote branches for {self.git_repo.name}: {str(e)}")
            return ['main', 'master']  # 返回常见默认分支

    def get_commit_history(self, limit=10):
        if not self.repo:
            if not self.clone_or_pull():
                return []
        
        try:
            commits = []
            for commit in self.repo.iter_commits(max_count=limit):
                commits.append({
                    'hash': commit.hexsha,
                    'message': commit.message.strip(),
                    'author': str(commit.author),
                    'date': commit.committed_datetime.isoformat(),
                    'files': list(commit.stats.files.keys())
                })
            return commits
            
        except Exception as e:
            logger.error(f"Failed to get commit history for {self.git_repo.name}: {str(e)}")
            return []