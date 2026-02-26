from django.contrib.auth.models import User
from django.db import models


class Exam(models.Model):
    teacher = models.ForeignKey(User, on_delete=models.CASCADE, related_name="created_exams")
    subject = models.CharField(max_length=200)
    title = models.CharField(max_length=200)
    duration_minutes = models.PositiveIntegerField(default=60)
    total_marks = models.PositiveIntegerField(default=100)
    scheduled_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.subject} - {self.title}"


class Question(models.Model):
    class QuestionType(models.TextChoices):
        MULTIPLE_CHOICE = "mcq", "Multiple Choice"
        THEORY = "theory", "Theory"

    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name="questions")
    text = models.TextField()
    question_type = models.CharField(max_length=10, choices=QuestionType.choices)
    marks = models.PositiveIntegerField(default=1)
    order = models.PositiveIntegerField(default=1)
    correct_answer = models.TextField(blank=True)

    class Meta:
        ordering = ["order", "id"]
        constraints = [
            models.UniqueConstraint(fields=["exam", "order"], name="unique_question_order_per_exam"),
        ]

    def __str__(self):
        return f"Q{self.order} ({self.question_type})"

    def grade_answer(self, selected_choice_id=None, theory_answer=""):
        if self.question_type == self.QuestionType.MULTIPLE_CHOICE:
            correct_choice = self.choices.filter(is_correct=True).first()
            if correct_choice and str(correct_choice.id) == str(selected_choice_id):
                return self.marks
            return 0

        if self.question_type == self.QuestionType.THEORY:
            expected = (self.correct_answer or "").strip().lower()
            provided = (theory_answer or "").strip().lower()
            if expected and provided and expected == provided:
                return self.marks
            return 0

        return 0


class Choice(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="choices")
    text = models.CharField(max_length=300)
    is_correct = models.BooleanField(default=False)

    def __str__(self):
        return self.text


class ExamEnrollment(models.Model):
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name="enrollments")
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name="exam_enrollments")
    enrolled_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("exam", "student")

    def __str__(self):
        return f"{self.student.username} -> {self.exam.title}"


class ExamResult(models.Model):
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name="results")
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name="exam_results")
    score = models.FloatField(default=0)
    correct_count = models.PositiveIntegerField(default=0)
    wrong_count = models.PositiveIntegerField(default=0)
    total_questions = models.PositiveIntegerField(default=0)
    time_taken_seconds = models.PositiveIntegerField(default=0)
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-submitted_at"]
        unique_together = ("exam", "student")

    def __str__(self):
        return f"{self.student.username} - {self.exam.title} ({self.score})"


class ExamSession(models.Model):
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name="sessions")
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name="exam_sessions")
    started_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    is_auto_submitted = models.BooleanField(default=False)
    is_flagged = models.BooleanField(default=False)
    warning_count = models.PositiveIntegerField(default=0)
    face_verified = models.BooleanField(default=False)
    face_verification_note = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-started_at"]

    def __str__(self):
        return f"{self.student.username} session - {self.exam.title}"


class StudentAnswer(models.Model):
    session = models.ForeignKey(ExamSession, on_delete=models.CASCADE, related_name="answers")
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="student_answers")
    selected_choice = models.ForeignKey(
        Choice,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="selected_in_answers",
    )
    theory_answer = models.TextField(blank=True)
    is_correct = models.BooleanField(default=False)
    awarded_marks = models.FloatField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["session", "question"], name="unique_answer_per_question_per_session"),
        ]

    def __str__(self):
        return f"{self.session.student.username} - Q{self.question.order}"
