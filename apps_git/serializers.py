from rest_framework import serializers
from django.contrib.auth.models import User
from .models import GitRepo


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']


class GitRepoSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    user = UserSerializer(read_only=True)

    class Meta:
        model = GitRepo
        fields = [
            'id', 'name', 'repo_url', 'username', 'password', 'branch', 
            'ssl_verify', 'is_active', 'created_at', 'updated_at', 'last_sync', 'user'
        ]
        read_only_fields = ['created_at', 'updated_at', 'last_sync']

    def create(self, validated_data):
        password = validated_data.pop('password')
        
        # 检查是否已存在相同用户和仓库URL的记录
        user = validated_data.get('user')
        repo_url = validated_data.get('repo_url')
        
        if user and repo_url:
            existing_repo = GitRepo.objects.filter(user=user, repo_url=repo_url).first()
            if existing_repo:
                # 如果已存在，更新现有记录而不是创建新记录
                for attr, value in validated_data.items():
                    setattr(existing_repo, attr, value)
                existing_repo.set_password(password)
                existing_repo.save()
                return existing_repo
        
        git_repo = GitRepo.objects.create(**validated_data)
        git_repo.set_password(password)
        git_repo.save()
        return git_repo

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        if password:
            instance.set_password(password)
        
        instance.save()
        return instance


class GitFileSerializer(serializers.Serializer):
    path = serializers.CharField()
    full_path = serializers.CharField()
    size = serializers.IntegerField()
    modified = serializers.FloatField()


class GitCommitSerializer(serializers.Serializer):
    hash = serializers.CharField()
    message = serializers.CharField()
    author = serializers.CharField()
    date = serializers.DateTimeField()
    files = serializers.ListField(child=serializers.CharField())


class FileContentSerializer(serializers.Serializer):
    file_path = serializers.CharField()
    content = serializers.CharField()


class CommitSerializer(serializers.Serializer):
    file_paths = serializers.ListField(child=serializers.CharField())
    commit_message = serializers.CharField()