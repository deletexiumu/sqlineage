import git
import os
import logging
from pathlib import Path
from urllib.parse import urlparse, urlunparse
from .models import GitRepo
from django.utils import timezone


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
        
        try:
            if os.path.exists(local_path):
                self.repo = git.Repo(local_path)
                origin = self.repo.remotes.origin
                logger.info(f"Pulling latest changes for {self.git_repo.name}")
                origin.pull()
            else:
                os.makedirs(os.path.dirname(local_path), exist_ok=True)
                logger.info(f"Cloning repository {self.git_repo.name}")
                self.repo = git.Repo.clone_from(
                    auth_url, 
                    local_path,
                    branch=self.git_repo.branch
                )
            
            self.git_repo.last_sync = timezone.now()
            self.git_repo.save()
            return True
            
        except Exception as e:
            logger.error(f"Failed to clone/pull repository {self.git_repo.name}: {str(e)}")
            return False

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
            origin.push()
            
            logger.info(f"Successfully committed and pushed changes to {self.git_repo.name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to commit and push to {self.git_repo.name}: {str(e)}")
            return False

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