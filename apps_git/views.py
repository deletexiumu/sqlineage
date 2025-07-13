from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
import os
import logging
from .models import GitRepo
from .serializers import (
    GitRepoSerializer, GitFileSerializer, GitCommitSerializer,
    FileContentSerializer, CommitSerializer, UserSerializer
)
from .git_service import GitService

logger = logging.getLogger(__name__)


class UserViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'])
    def me(self, request):
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)


class GitRepoViewSet(viewsets.ModelViewSet):
    serializer_class = GitRepoSerializer
    permission_classes = [IsAuthenticated]  # Git仓库操作需要登录

    def get_queryset(self):
        # 返回当前用户的仓库
        return GitRepo.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        # 关联当前认证用户
        serializer.save(user=self.request.user)
    
    def create(self, request, *args, **kwargs):
        """重写create方法以提供更好的错误处理"""
        try:
            return super().create(request, *args, **kwargs)
        except Exception as e:
            # 记录详细错误信息
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"GitRepo creation error: {str(e)}")
            
            return Response({
                'error': '创建Git仓库配置失败',
                'details': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def sync(self, request, pk=None):
        git_repo = self.get_object()
        git_service = GitService(git_repo)
        
        try:
            success = git_service.clone_or_pull()
            if success:
                return Response({'status': 'success', 'message': 'Repository synced successfully'})
            else:
                return Response(
                    {'status': 'error', 'message': 'Failed to sync repository'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        except Exception as e:
            error_message = str(e)
            
            # 检查是否是需要重新clone的错误
            if "建议删除本地仓库重新同步" in error_message or "仓库状态异常" in error_message:
                return Response({
                    'status': 'error',
                    'message': '仓库状态异常，建议重新同步',
                    'action': 'force_reclone',
                    'details': error_message
                }, status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response({
                    'status': 'error',
                    'message': '仓库同步失败',
                    'details': error_message
                }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def force_reclone(self, request, pk=None):
        """强制重新克隆仓库"""
        git_repo = self.get_object()
        
        try:
            # 删除本地仓库目录
            local_path = git_repo.repo_local_path
            if os.path.exists(local_path):
                import shutil
                shutil.rmtree(local_path)
                logger.info(f"Removed corrupted repository at {local_path}")
            
            # 重新克隆
            git_service = GitService(git_repo)
            success = git_service.clone_or_pull()
            
            if success:
                return Response({
                    'status': 'success', 
                    'message': '仓库重新克隆成功'
                })
            else:
                return Response({
                    'status': 'error', 
                    'message': '重新克隆失败'
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            return Response({
                'status': 'error',
                'message': '重新克隆失败',
                'details': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def files(self, request, pk=None):
        git_repo = self.get_object()
        git_service = GitService(git_repo)
        
        sql_files = git_service.get_sql_files()
        serializer = GitFileSerializer(sql_files, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def read_file(self, request, pk=None):
        git_repo = self.get_object()
        git_service = GitService(git_repo)
        
        file_path = request.data.get('file_path')
        if not file_path:
            return Response(
                {'error': 'file_path is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        content = git_service.read_file(file_path)
        if content is None:
            return Response(
                {'error': 'File not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        return Response({'file_path': file_path, 'content': content})

    @action(detail=True, methods=['post'])
    def write_file(self, request, pk=None):
        git_repo = self.get_object()
        git_service = GitService(git_repo)
        
        serializer = FileContentSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        file_path = serializer.validated_data['file_path']
        content = serializer.validated_data['content']
        
        success = git_service.write_file(file_path, content)
        if success:
            return Response({'status': 'success', 'message': 'File written successfully'})
        else:
            return Response(
                {'status': 'error', 'message': 'Failed to write file'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def commit(self, request, pk=None):
        git_repo = self.get_object()
        git_service = GitService(git_repo)
        
        serializer = CommitSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        file_paths = serializer.validated_data['file_paths']
        commit_message = serializer.validated_data['commit_message']
        
        success = git_service.commit_and_push(file_paths, commit_message)
        if success:
            return Response({'status': 'success', 'message': 'Changes committed and pushed successfully'})
        else:
            return Response(
                {'status': 'error', 'message': 'Failed to commit and push changes'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['get'])
    def branches(self, request, pk=None):
        """获取远程仓库的分支列表"""
        git_repo = self.get_object()
        git_service = GitService(git_repo)
        
        try:
            branches = git_service.get_remote_branches()
            return Response({
                'branches': branches,
                'current_branch': git_repo.branch,
                'status': 'success'
            })
        except Exception as e:
            return Response({
                'error': '获取分支列表失败',
                'details': str(e),
                'branches': ['main', 'master'],  # 默认分支
                'status': 'error'
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def switch_branch(self, request, pk=None):
        """切换仓库分支"""
        git_repo = self.get_object()
        new_branch = request.data.get('branch')
        
        if not new_branch:
            return Response({
                'error': '分支名称不能为空'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 更新仓库配置中的分支
        git_repo.branch = new_branch
        git_repo.save()
        
        return Response({
            'status': 'success',
            'message': f'分支已切换到 {new_branch}',
            'current_branch': new_branch
        })

    @action(detail=True, methods=['get'])
    def commits(self, request, pk=None):
        git_repo = self.get_object()
        git_service = GitService(git_repo)
        
        limit = int(request.query_params.get('limit', 10))
        commits = git_service.get_commit_history(limit)
        serializer = GitCommitSerializer(commits, many=True)
        return Response(serializer.data)
    
    def destroy(self, request, *args, **kwargs):
        """删除Git仓库配置，同时清理本地文件"""
        git_repo = self.get_object()
        
        try:
            # 删除本地仓库目录
            local_path = git_repo.repo_local_path
            if os.path.exists(local_path):
                import shutil
                import platform
                import stat
                
                # Windows下需要特殊处理只读文件
                if platform.system() == 'Windows':
                    def remove_readonly_handler(func, path, exc_info):
                        """处理Windows只读文件删除问题"""
                        if os.path.exists(path):
                            os.chmod(path, stat.S_IWRITE)
                            func(path)
                    
                    shutil.rmtree(local_path, onerror=remove_readonly_handler)
                else:
                    shutil.rmtree(local_path)
                    
                logger.info(f"Removed local repository at {local_path}")
            
            # 删除数据库记录
            repo_name = git_repo.name
            git_repo.delete()
            
            return Response({
                'status': 'success',
                'message': f'仓库 {repo_name} 及本地文件已删除'
            })
            
        except Exception as e:
            logger.error(f"Failed to delete repository {git_repo.name}: {str(e)}")
            return Response({
                'status': 'error',
                'message': '删除仓库失败',
                'details': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
