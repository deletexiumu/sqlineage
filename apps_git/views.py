from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from .models import GitRepo
from .serializers import (
    GitRepoSerializer, GitFileSerializer, GitCommitSerializer,
    FileContentSerializer, CommitSerializer, UserSerializer
)
from .git_service import GitService


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
    permission_classes = [AllowAny]  # 暂时允许匿名访问，适合内部使用

    def get_queryset(self):
        # 如果用户已认证，返回用户的仓库；否则返回所有仓库（适合内部使用）
        if self.request.user.is_authenticated:
            return GitRepo.objects.filter(user=self.request.user)
        else:
            return GitRepo.objects.all()

    def perform_create(self, serializer):
        # 如果用户已认证，关联用户；否则关联默认用户
        if self.request.user.is_authenticated:
            serializer.save(user=self.request.user)
        else:
            # 获取或创建默认用户
            default_user, created = User.objects.get_or_create(
                username='default',
                defaults={'email': 'default@example.com'}
            )
            serializer.save(user=default_user)
    
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
        
        success = git_service.clone_or_pull()
        if success:
            return Response({'status': 'success', 'message': 'Repository synced successfully'})
        else:
            return Response(
                {'status': 'error', 'message': 'Failed to sync repository'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

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
