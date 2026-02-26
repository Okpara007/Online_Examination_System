from django.urls import path

from . import views

urlpatterns = [
    path("dashboard/", views.teacher_dashboard, name="teacher_dashboard"),
    path("exams/", views.teacher_exam_list, name="teacher_exam_list"),
    path("exams/create/", views.teacher_exam_create, name="teacher_exam_create"),
    path("exams/<int:exam_id>/edit/", views.teacher_exam_edit, name="teacher_exam_edit"),
    path("exams/<int:exam_id>/delete/", views.teacher_exam_delete, name="teacher_exam_delete"),
    path("exams/<int:exam_id>/questions/", views.teacher_question_list, name="teacher_question_list"),
    path("exams/<int:exam_id>/questions/create/", views.teacher_question_create, name="teacher_question_create"),
    path("exams/<int:exam_id>/questions/<int:question_id>/edit/", views.teacher_question_edit, name="teacher_question_edit"),
    path("exams/<int:exam_id>/questions/<int:question_id>/delete/", views.teacher_question_delete, name="teacher_question_delete"),
    path("exams/<int:exam_id>/questions/<int:question_id>/choices/", views.teacher_choice_list, name="teacher_choice_list"),
    path("exams/<int:exam_id>/questions/<int:question_id>/choices/create/", views.teacher_choice_create, name="teacher_choice_create"),
    path(
        "exams/<int:exam_id>/questions/<int:question_id>/choices/<int:choice_id>/edit/",
        views.teacher_choice_edit,
        name="teacher_choice_edit",
    ),
    path(
        "exams/<int:exam_id>/questions/<int:question_id>/choices/<int:choice_id>/delete/",
        views.teacher_choice_delete,
        name="teacher_choice_delete",
    ),
    path("exams/<int:exam_id>/enrollments/", views.teacher_exam_enrollments, name="teacher_exam_enrollments"),
    path(
        "exams/<int:exam_id>/enrollments/<int:enrollment_id>/delete/",
        views.teacher_enrollment_delete,
        name="teacher_enrollment_delete",
    ),
    path("results/", views.teacher_results, name="teacher_results"),
    path("exams/<int:exam_id>/results/report/", views.teacher_exam_result_report, name="teacher_exam_result_report"),
    path("proctoring/", views.teacher_proctoring_logs, name="teacher_proctoring_logs"),
    path("exams/<int:exam_id>/proctoring/create/", views.teacher_proctoring_log_create, name="teacher_proctoring_log_create"),
    path("analytics/", views.teacher_analytics, name="teacher_analytics"),
    path("reports/results.csv", views.teacher_export_results_csv, name="teacher_export_results_csv"),
    path("reports/proctoring.csv", views.teacher_export_proctoring_csv, name="teacher_export_proctoring_csv"),
]
