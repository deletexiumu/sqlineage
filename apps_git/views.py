from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
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
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return GitRepo.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

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
    def commits(self, request, pk=None):
        git_repo = self.get_object()
        git_service = GitService(git_repo)
        
        limit = int(request.query_params.get('limit', 10))
        commits = git_service.get_commit_history(limit)
        serializer = GitCommitSerializer(commits, many=True)
        return Response(serializer.data)
