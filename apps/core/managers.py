from django.db import models
from django.utils import timezone


class SoftDeleteManager(models.Manager):
    """
    Manager that filters out soft-deleted objects
    """
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)


class AllObjectsManager(models.Manager):
    """
    Manager that returns all objects including soft-deleted ones
    """
    def get_queryset(self):
        return super().get_queryset()