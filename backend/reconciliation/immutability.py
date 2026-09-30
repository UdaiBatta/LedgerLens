import hashlib
import json

from django.core.exceptions import ValidationError
from django.db import models


def content_digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


class AppendOnlyQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise ValidationError("Immutable records cannot be updated; append new evidence instead.")

    def delete(self):
        raise ValidationError("Immutable records cannot be deleted.")

    def bulk_update(self, *args, **kwargs):
        raise ValidationError("Immutable records cannot be bulk updated.")

    def bulk_create(self, *args, **kwargs):
        raise ValidationError("Use validated record creation, not bulk_create.")


class AppendOnlyModel(models.Model):
    objects = AppendOnlyQuerySet.as_manager()

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValidationError("Immutable records cannot be saved again.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Immutable records cannot be deleted.")
