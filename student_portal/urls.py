from django.urls import path

from . import views

urlpatterns = [
    path("dashboard/", views.student_dashboard, name="student_dashboard"),
    path("exams/<int:exam_id>/start/", views.student_exam_start, name="student_exam_start"),
    path("exams/<int:exam_id>/take/", views.student_take_exam, name="student_take_exam"),
    path("exams/<int:exam_id>/submit/", views.student_submit_exam, name="student_submit_exam"),
    path("exams/<int:exam_id>/proctor-event/", views.student_proctor_event, name="student_proctor_event"),
    path("results/", views.student_results, name="student_results"),
    path("results/<int:result_id>/", views.student_result_detail, name="student_result_detail"),
]
