from django.contrib import admin

from .models import Choice, Exam, ExamEnrollment, ExamResult, ExamSession, Question, StudentAnswer


@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = ("title", "subject", "teacher", "scheduled_at", "total_marks")
    search_fields = ("title", "subject", "teacher__username")
    list_filter = ("subject",)


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("exam", "order", "question_type", "marks")
    list_filter = ("question_type",)


@admin.register(Choice)
class ChoiceAdmin(admin.ModelAdmin):
    list_display = ("question", "text", "is_correct")
    list_filter = ("is_correct",)


@admin.register(ExamEnrollment)
class ExamEnrollmentAdmin(admin.ModelAdmin):
    list_display = ("exam", "student", "enrolled_at")


@admin.register(ExamResult)
class ExamResultAdmin(admin.ModelAdmin):
    list_display = ("exam", "student", "score", "submitted_at")
    list_filter = ("exam",)


@admin.register(ExamSession)
class ExamSessionAdmin(admin.ModelAdmin):
    list_display = ("exam", "student", "started_at", "submitted_at", "is_auto_submitted", "warning_count", "is_flagged")
    list_filter = ("is_auto_submitted", "is_flagged")


@admin.register(StudentAnswer)
class StudentAnswerAdmin(admin.ModelAdmin):
    list_display = ("session", "question", "is_correct", "awarded_marks")
