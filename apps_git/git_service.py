import git
import os
import logging
import ssl
import urllib3
from pathlib import Path
from urllib.parse import urlparse, urlunparse
from .models import GitRepo
from django.utils import timezone

# 禁用urllib3的SSL警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


logger = logging.getLogger(__name__)


class GitService:
    def __init__(self, git_repo: GitRepo):
        self.git_repo = git_repo
        self.repo = None

    def _get_auth_url(self):
        parsed = urlparse(self.git_repo.repo_url)
        password = self.git_repo.get_password()
        
        # 根据认证类型构建URL
        if self.git_repo.auth_type == 'token':
            # GitLab Token认证: 对于GitLab私有部署，推荐使用以下格式之一
            # 1. 直接使用token作为用户名，密码留空
            # 2. 使用token作为密码，用户名为任意值
            # 3. 特殊格式: <username>:<token>
            
            # 尝试多种GitLab Token认证格式
            # 格式1: token作为用户名，密码留空
            if not hasattr(self, '_auth_format_tried'):
                self._auth_format_tried = 0
            
            if self._auth_format_tried == 0:
                # 第一次尝试：token作为用户名
                auth_netloc = f"{password}:@{parsed.netloc}"
            elif self._auth_format_tried == 1:
                # 第二次尝试：任意用户名+token作为密码
                auth_netloc = f"gitlab-ci-token:{password}@{parsed.netloc}"
            elif self._auth_format_tried == 2:
                # 第三次尝试：用设置的用户名+token
                username = self.git_repo.username if self.git_repo.username else 'git'
                auth_netloc = f"{username}:{password}@{parsed.netloc}"
            else:
                # 最后尝试：oauth2格式
                auth_netloc = f"oauth2:{password}@{parsed.netloc}"
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
        
        logger.info(f"Using auth URL format for {self.git_repo.auth_type}: {parsed.scheme}://<credentials>@{parsed.netloc}{parsed.path}")
        return auth_url

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

    def clone_or_pull(self):
        local_path = self.git_repo.repo_local_path
        auth_url = self._get_auth_url()
        
        # 清理可能的凭据缓存问题
        self._clear_git_credentials()
        
        # 配置SSL验证选项
        env_vars = {}
        if not self.git_repo.ssl_verify:
            # 禁用SSL验证的环境变量
            env_vars.update({
                'GIT_SSL_NO_VERIFY': '1',
                'GIT_CURL_VERBOSE': '0'
            })
            logger.info(f"SSL verification disabled for {self.git_repo.name}")
        
        # 禁用凭据缓存，强制使用URL中的认证信息
        env_vars.update({
            'GIT_TERMINAL_PROMPT': '0',  # 禁用交互式提示
            'GIT_ASKPASS': 'echo',       # 禁用密码提示
        })
        
        try:
            if os.path.exists(local_path):
                try:
                    self.repo = git.Repo(local_path)
                    origin = self.repo.remotes.origin
                    logger.info(f"Pulling latest changes for {self.git_repo.name}")
                    
                    # 检查并设置remote refspec
                    try:
                        # 尝试获取remote的refspec配置
                        origin.refs
                    except (AttributeError, AssertionError):
                        # 如果refspec没有正确设置，重新配置
                        logger.info(f"Setting up remote refspec for {self.git_repo.name}")
                        self.repo.git.config('remote.origin.fetch', '+refs/heads/*:refs/heads/*')
                except (git.exc.InvalidGitRepositoryError, git.exc.NoSuchPathError) as repo_error:
                    # 如果本地仓库损坏，删除并重新clone
                    logger.warning(f"Local repository corrupted for {self.git_repo.name}, removing and re-cloning")
                    import shutil
                    shutil.rmtree(local_path)
                    return self.clone_or_pull()  # 递归调用进行clone
                
                # 使用底层Git命令绕过GitPython的refspec检查
                with self.repo.git.custom_environment(**env_vars):
                    # 禁用凭据助手，强制使用URL认证
                    self.repo.git.config('credential.helper', '')
                    
                    # 直接使用git命令设置refspec和fetch
                    self.repo.git.config('remote.origin.fetch', '+refs/heads/*:refs/heads/*')
                    
                    # 更新remote URL以包含认证信息
                    self.repo.git.remote('set-url', 'origin', auth_url)
                    
                    # 使用git命令行直接fetch
                    self.repo.git.fetch('origin')
                    
                    # 获取当前分支或目标分支
                    try:
                        current_branch = self.repo.active_branch.name
                    except:
                        # 如果没有active branch，使用配置的分支
                        current_branch = self.git_repo.branch
                    
                    # 检查远程分支是否存在
                    try:
                        # 先检查仓库状态
                        try:
                            # 尝试获取当前HEAD状态
                            self.repo.git.rev_parse('HEAD')
                            has_head = True
                        except git.exc.GitCommandError:
                            has_head = False
                            logger.info(f"Repository {self.git_repo.name} has no HEAD, will initialize")
                        
                        # 获取远程分支列表的更安全方式
                        try:
                            remote_refs_output = self.repo.git.ls_remote('--heads', 'origin')
                            remote_branches = []
                            for line in remote_refs_output.split('\n'):
                                if line.strip() and 'refs/heads/' in line:
                                    branch_name = line.split('refs/heads/')[-1].strip()
                                    remote_branches.append(branch_name)
                        except git.exc.GitCommandError:
                            # 如果ls-remote失败，使用fetch后的本地引用
                            try:
                                branch_output = self.repo.git.branch('-r')
                                remote_branches = [b.strip().replace('origin/', '') 
                                                 for b in branch_output.split('\n') 
                                                 if 'origin/' in b and '->' not in b and b.strip()]
                            except git.exc.GitCommandError:
                                # 最后的备选方案
                                remote_branches = ['main', 'master']
                        
                        # 如果目标分支不在远程分支列表中，选择默认分支
                        if current_branch not in remote_branches:
                            if 'main' in remote_branches:
                                current_branch = 'main'
                            elif 'master' in remote_branches:
                                current_branch = 'master'
                            elif remote_branches:
                                current_branch = remote_branches[0]  # 使用第一个可用分支
                            
                            logger.info(f"Switching to available branch: {current_branch}")
                        
                        # 安全地切换到目标分支
                        try:
                            if has_head:
                                # 如果有HEAD，正常切换分支
                                self.repo.git.checkout('-B', current_branch, f'origin/{current_branch}')
                            else:
                                # 如果没有HEAD，需要先创建初始分支
                                try:
                                    self.repo.git.checkout('-b', current_branch, f'origin/{current_branch}')
                                except git.exc.GitCommandError:
                                    # 如果还是失败，尝试直接reset
                                    self.repo.git.symbolic_ref('HEAD', f'refs/heads/{current_branch}')
                                    self.repo.git.reset('--hard', f'origin/{current_branch}')
                        except git.exc.GitCommandError as checkout_error:
                            logger.warning(f"Checkout failed: {checkout_error}, trying alternative approach")
                            # 备选方案：直接设置HEAD和reset
                            try:
                                self.repo.git.symbolic_ref('HEAD', f'refs/heads/{current_branch}')
                                self.repo.git.reset('--hard', f'origin/{current_branch}')
                            except git.exc.GitCommandError as reset_error:
                                logger.error(f"Reset also failed: {reset_error}")
                                # 最后的备选方案：强制重新clone
                                raise Exception(f"无法切换到分支 {current_branch}，仓库状态异常")
                        
                    except git.exc.GitCommandError as e:
                        logger.error(f"Branch operation failed: {str(e)}")
                        # 如果所有分支操作都失败，标记需要重新clone
                        raise Exception(f"分支操作失败，建议删除本地仓库重新同步: {str(e)}")
            else:
                os.makedirs(os.path.dirname(local_path), exist_ok=True)
                logger.info(f"Cloning repository {self.git_repo.name}")
                
                # 设置git配置选项
                clone_env = dict(os.environ)
                clone_env.update(env_vars)
                
                self.repo = git.Repo.clone_from(
                    auth_url, 
                    local_path,
                    branch=self.git_repo.branch,
                    env=clone_env
                )
                
                # 确保remote refspec正确设置
                self.repo.git.config('remote.origin.fetch', '+refs/heads/*:refs/heads/*')
                
                # 禁用凭据助手，避免Windows凭据管理器干扰
                self.repo.git.config('credential.helper', '')
                
                # 为仓库设置ssl配置
                if not self.git_repo.ssl_verify:
                    self.repo.git.config('http.sslVerify', 'false')
                    self.repo.git.config('https.sslVerify', 'false')
            
            self.git_repo.last_sync = timezone.now()
            self.git_repo.save()
            return True
            
        except git.exc.GitCommandError as e:
            error_msg = str(e)
            
            # 检查是否是认证错误
            if ('Authentication failed' in error_msg or 
                'access denied' in error_msg.lower() or 
                'HTTP Basic: Access denied' in error_msg):
                
                # 如果是Token认证失败，尝试其他认证格式
                if (self.git_repo.auth_type == 'token' and 
                    hasattr(self, '_auth_format_tried') and 
                    self._auth_format_tried < 3):
                    
                    self._auth_format_tried += 1
                    logger.warning(f"Token auth failed, trying format {self._auth_format_tried} for {self.git_repo.name}")
                    
                    # 清理失败的clone目录
                    if os.path.exists(local_path):
                        import shutil
                        shutil.rmtree(local_path)
                    
                    # 递归重试
                    return self.clone_or_pull()
                else:
                    logger.error(f"Authentication failed for {self.git_repo.name}: {error_msg}")
                    raise Exception(f"认证失败: 请检查用户名、密码或Token是否正确。详细错误: {error_msg}")
                    
            elif 'certificate verify failed' in error_msg or 'SSL certificate problem' in error_msg:
                logger.error(f"SSL certificate error for {self.git_repo.name}. Try disabling SSL verification.")
                raise Exception("SSL证书验证失败，请在仓库配置中关闭SSL验证选项")
            else:
                logger.error(f"Git command failed for {self.git_repo.name}: {error_msg}")
                raise Exception(f"Git操作失败: {error_msg}")
        except Exception as e:
            logger.error(f"Failed to clone/pull repository {self.git_repo.name}: {str(e)}")
            raise Exception(f"仓库同步失败: {str(e)}")

    def get_sql_files(self):
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
                        'modified': sql_file.stat().st_mtime
                    })
            
            sql_files.sort(key=lambda x: x['path'])
            return sql_files
            
        except Exception as e:
            logger.error(f"Failed to get SQL files from {self.git_repo.name}: {str(e)}")
            return []

    def read_file(self, file_path):
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
        """获取远程仓库的分支列表"""
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