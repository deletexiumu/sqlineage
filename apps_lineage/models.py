from django.db import models
from apps_metadata.models import HiveTable
import json


class LineageRelation(models.Model):
    source_table = models.ForeignKey(
        HiveTable, 
        on_delete=models.CASCADE, 
        related_name='outgoing_relations'
    )
    target_table = models.ForeignKey(
        HiveTable, 
        on_delete=models.CASCADE, 
        related_name='incoming_relations'
    )
    sql_script_path = models.CharField(max_length=500, blank=True)
    relation_type = models.CharField(max_length=50, default='insert')
    process_id = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['source_table', 'target_table', 'sql_script_path']

    def __str__(self):
        return f"{self.source_table.full_name} -> {self.target_table.full_name}"


class ColumnLineage(models.Model):
    relation = models.ForeignKey(LineageRelation, on_delete=models.CASCADE, related_name='column_lineages')
    source_column = models.CharField(max_length=255)
    target_column = models.CharField(max_length=255)
    transformation = models.TextField(blank=True)

    class Meta:
        unique_together = ['relation', 'source_column', 'target_column']

    def __str__(self):
        return f"{self.source_column} -> {self.target_column}"


class LineageParseJob(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('running', 'Running'), 
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    PARSE_TYPE_CHOICES = [
        ('full', 'Full Parse'),
        ('incremental', 'Incremental Parse'),
        ('full_overwrite', 'Full Overwrite Parse'),
    ]
    
    git_repo = models.ForeignKey('apps_git.GitRepo', on_delete=models.CASCADE, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    parse_type = models.CharField(max_length=20, choices=PARSE_TYPE_CHOICES, default='full')
    total_files = models.IntegerField(default=0)
    processed_files = models.IntegerField(default=0)
    failed_files = models.IntegerField(default=0)
    error_message = models.TextField(blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        repo_name = self.git_repo.name if self.git_repo else "Manual"
        return f"Lineage Job {self.id} - {repo_name} ({self.status})"

    @property
    def progress_percentage(self):
        if self.total_files == 0:
            return 0
        return (self.processed_files / self.total_files) * 100
