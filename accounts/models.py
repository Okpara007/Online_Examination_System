from django.db import models
from django.contrib.auth.models import User


class UserProfile(models.Model):
    class Role(models.TextChoices):
        TEACHER = "teacher", "Teacher"
        STUDENT = "student", "Student"

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    role = models.CharField(max_length=20, choices=Role.choices)
    face_image = models.ImageField(upload_to="face_profiles/", null=True, blank=True)

    @property
    def is_teacher(self):
        return self.role == self.Role.TEACHER

    @property
    def is_student(self):
        return self.role == self.Role.STUDENT

    def __str__(self):
        return f"{self.user.username} ({self.role})"
