from django.contrib.auth.models import User
from django.db import models

from exams.models import Exam


class ProctoringLog(models.Model):
    class Severity(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"

    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name="proctoring_logs")
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="proctoring_logs",
        null=True,
        blank=True,
    )
    event_type = models.CharField(max_length=150)
    details = models.TextField(blank=True)
    severity = models.CharField(max_length=10, choices=Severity.choices, default=Severity.LOW)
    is_flagged = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.exam.title} - {self.event_type}"
