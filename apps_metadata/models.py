from django.db import models
import json


class HiveTable(models.Model):
    name = models.CharField(max_length=255)
    database = models.CharField(max_length=255)
    columns_json = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['name', 'database']

    def __str__(self):
        return f"{self.database}.{self.name}"

    @property
    def columns(self):
        try:
            return json.loads(self.columns_json)
        except json.JSONDecodeError:
            return []

    @columns.setter
    def columns(self, value):
        self.columns_json = json.dumps(value)

    @property
    def full_name(self):
        return f"{self.database}.{self.name}"


class BusinessMapping(models.Model):
    table = models.ForeignKey(HiveTable, on_delete=models.CASCADE)
    application_name = models.CharField(max_length=255)
    module_name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['table', 'application_name', 'module_name']

    def __str__(self):
        return f"{self.table.full_name} -> {self.application_name}.{self.module_name}"
