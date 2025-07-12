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
        auth_netloc = f"{self.git_repo.username}:{self.git_repo.get_password()}@{parsed.netloc}"
        auth_url = urlunparse((
            parsed.scheme,
            auth_netloc,
            parsed.path,
            parsed.params,
            parsed.query,
            parsed.fragment
        ))
        return auth_url

    def clone_or_pull(self):
        local_path = self.git_repo.repo_local_path
        auth_url = self._get_auth_url()
        
        # 配置SSL验证选项
        env_vars = {}
        if not self.git_repo.ssl_verify:
            # 禁用SSL验证的环境变量
            env_vars.update({
                'GIT_SSL_NO_VERIFY': '1',
                'GIT_CURL_VERBOSE': '0'
            })
            logger.info(f"SSL verification disabled for {self.git_repo.name}")
        
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
                    # 直接使用git命令设置refspec和fetch
                    self.repo.git.config('remote.origin.fetch', '+refs/heads/*:refs/heads/*')
                    
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
                        # 列出所有远程分支
                        remote_branches = self.repo.git.branch('-r').split('\n')
                        remote_branches = [b.strip().replace('origin/', '') for b in remote_branches if 'origin/' in b and '->' not in b]
                        
                        # 如果目标分支不在远程分支列表中，使用默认分支
                        if current_branch not in remote_branches:
                            if 'main' in remote_branches:
                                current_branch = 'main'
                            elif 'master' in remote_branches:
                                current_branch = 'master'
                            elif remote_branches:
                                current_branch = remote_branches[0]  # 使用第一个可用分支
                            
                            logger.info(f"Switching to available branch: {current_branch}")
                        
                        # 切换到目标分支
                        self.repo.git.checkout('-B', current_branch, f'origin/{current_branch}')
                        
                    except git.exc.GitCommandError as e:
                        logger.error(f"Branch operation failed: {str(e)}")
                        # 尝试reset到remote HEAD
                        self.repo.git.reset('--hard', 'origin/HEAD')
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
                
                # 为仓库设置ssl配置
                if not self.git_repo.ssl_verify:
                    self.repo.git.config('http.sslVerify', 'false')
                    self.repo.git.config('https.sslVerify', 'false')
            
            self.git_repo.last_sync = timezone.now()
            self.git_repo.save()
            return True
            
        except git.exc.GitCommandError as e:
            if 'certificate verify failed' in str(e) or 'SSL certificate problem' in str(e):
                logger.error(f"SSL certificate error for {self.git_repo.name}. Try disabling SSL verification.")
                raise Exception("SSL证书验证失败，请在仓库配置中关闭SSL验证选项")
            else:
                logger.error(f"Git command failed for {self.git_repo.name}: {str(e)}")
                raise Exception(f"Git操作失败: {str(e)}")
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
                    self.repo.git.fetch('origin')
                    
                    # 获取远程分支列表
                    remote_branches = self.repo.git.branch('-r').split('\n')
                    branches = [b.strip().replace('origin/', '') for b in remote_branches if 'origin/' in b and '->' not in b]
                    
                    return branches
                    
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