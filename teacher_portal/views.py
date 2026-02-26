import csv
from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count, Max, Min, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from accounts.utils import dashboard_url_for_user
from exams.models import Choice, Exam, ExamEnrollment, ExamResult, Question
from proctoring.models import ProctoringLog
from .forms import ChoiceForm, ExamEnrollmentForm, ExamForm, ProctoringLogForm, QuestionForm


def teacher_required(view_func):
    @wraps(view_func)
    @login_required
    def _wrapped(request, *args, **kwargs):
        profile = getattr(request.user, "profile", None)
        if not profile or not profile.is_teacher:
            messages.error(request, "Teacher access is required.")
            return redirect(dashboard_url_for_user(request.user))
        return view_func(request, *args, **kwargs)

    return _wrapped


@teacher_required
def teacher_dashboard(request):
    exams = Exam.objects.filter(teacher=request.user)
    flagged_count = ProctoringLog.objects.filter(exam__teacher=request.user, is_flagged=True).count()
    context = {
        "exam_count": exams.count(),
        "question_count": Question.objects.filter(exam__teacher=request.user).count(),
        "result_count": ExamResult.objects.filter(exam__teacher=request.user).count(),
        "flagged_count": flagged_count,
        "recent_exams": exams[:5],
    }
    return render(request, "teacher_portal/dashboard.html", context)


@teacher_required
def teacher_exam_list(request):
    exams = (
        Exam.objects.filter(teacher=request.user)
        .annotate(
            question_count=Count("questions", distinct=True),
            result_count=Count("results", distinct=True),
            flagged_count=Count("proctoring_logs", filter=Q(proctoring_logs__is_flagged=True), distinct=True),
        )
        .order_by("-created_at")
    )
    return render(request, "teacher_portal/exam_list.html", {"exams": exams})


@teacher_required
def teacher_exam_create(request):
    if request.method == "POST":
        form = ExamForm(request.POST)
        if form.is_valid():
            exam = form.save(commit=False)
            exam.teacher = request.user
            exam.save()
            messages.success(request, "Exam created.")
            return redirect("teacher_exam_list")
    else:
        form = ExamForm()
    return render(request, "teacher_portal/exam_form.html", {"form": form, "page_title": "Create Exam"})


@teacher_required
def teacher_exam_edit(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id, teacher=request.user)
    if request.method == "POST":
        form = ExamForm(request.POST, instance=exam)
        if form.is_valid():
            form.save()
            messages.success(request, "Exam updated.")
            return redirect("teacher_exam_list")
    else:
        form = ExamForm(instance=exam)
    return render(request, "teacher_portal/exam_form.html", {"form": form, "page_title": "Edit Exam"})


@teacher_required
def teacher_exam_delete(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id, teacher=request.user)
    if request.method == "POST":
        exam.delete()
        messages.success(request, "Exam deleted.")
        return redirect("teacher_exam_list")
    return render(request, "teacher_portal/exam_delete.html", {"exam": exam})


@teacher_required
def teacher_question_list(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id, teacher=request.user)
    questions = exam.questions.prefetch_related("choices")
    return render(request, "teacher_portal/question_list.html", {"exam": exam, "questions": questions})


@teacher_required
def teacher_question_create(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id, teacher=request.user)
    if request.method == "POST":
        form = QuestionForm(request.POST)
        if form.is_valid():
            question = form.save(commit=False)
            question.exam = exam
            max_order = exam.questions.aggregate(max_order=Max("order"))["max_order"] or 0
            question.order = max_order + 1
            question.save()
            if question.question_type == Question.QuestionType.MULTIPLE_CHOICE:
                options = form.cleaned_data.get("parsed_options", [])
                correct_idx = int(form.cleaned_data["correct_option"])
                question.choices.all().delete()
                for idx, option_text in enumerate(options):
                    Choice.objects.create(
                        question=question,
                        text=option_text,
                        is_correct=idx == correct_idx,
                    )
            else:
                question.choices.all().delete()
            messages.success(request, "Question added.")
            return redirect("teacher_question_list", exam_id=exam.id)
    else:
        form = QuestionForm()
    return render(
        request,
        "teacher_portal/question_form.html",
        {"form": form, "exam": exam, "page_title": "Add Question"},
    )


@teacher_required
def teacher_question_edit(request, exam_id, question_id):
    exam = get_object_or_404(Exam, id=exam_id, teacher=request.user)
    question = get_object_or_404(Question, id=question_id, exam=exam)
    if request.method == "POST":
        form = QuestionForm(request.POST, instance=question)
        if form.is_valid():
            updated_question = form.save()
            if updated_question.question_type == Question.QuestionType.MULTIPLE_CHOICE:
                options = form.cleaned_data.get("parsed_options", [])
                correct_idx = int(form.cleaned_data["correct_option"])
                updated_question.choices.all().delete()
                for idx, option_text in enumerate(options):
                    Choice.objects.create(
                        question=updated_question,
                        text=option_text,
                        is_correct=idx == correct_idx,
                    )
            else:
                updated_question.choices.all().delete()
            messages.success(request, "Question updated.")
            return redirect("teacher_question_list", exam_id=exam.id)
    else:
        form = QuestionForm(instance=question)
    return render(
        request,
        "teacher_portal/question_form.html",
        {"form": form, "exam": exam, "page_title": "Edit Question"},
    )


@teacher_required
def teacher_question_delete(request, exam_id, question_id):
    exam = get_object_or_404(Exam, id=exam_id, teacher=request.user)
    question = get_object_or_404(Question, id=question_id, exam=exam)
    if request.method == "POST":
        question.delete()
        messages.success(request, "Question deleted.")
        return redirect("teacher_question_list", exam_id=exam.id)
    return render(request, "teacher_portal/question_delete.html", {"exam": exam, "question": question})


@teacher_required
def teacher_choice_list(request, exam_id, question_id):
    exam = get_object_or_404(Exam, id=exam_id, teacher=request.user)
    question = get_object_or_404(Question, id=question_id, exam=exam)
    if question.question_type != Question.QuestionType.MULTIPLE_CHOICE:
        messages.error(request, "Choices are only available for multiple-choice questions.")
        return redirect("teacher_question_list", exam_id=exam.id)
    return render(
        request,
        "teacher_portal/choice_list.html",
        {"exam": exam, "question": question, "choices": question.choices.all()},
    )


@teacher_required
def teacher_choice_create(request, exam_id, question_id):
    exam = get_object_or_404(Exam, id=exam_id, teacher=request.user)
    question = get_object_or_404(Question, id=question_id, exam=exam)
    if question.question_type != Question.QuestionType.MULTIPLE_CHOICE:
        messages.error(request, "Choices are only available for multiple-choice questions.")
        return redirect("teacher_question_list", exam_id=exam.id)

    if request.method == "POST":
        form = ChoiceForm(request.POST)
        if form.is_valid():
            choice = form.save(commit=False)
            choice.question = question
            choice.save()
            messages.success(request, "Choice added.")
            return redirect("teacher_choice_list", exam_id=exam.id, question_id=question.id)
    else:
        form = ChoiceForm()

    return render(
        request,
        "teacher_portal/choice_form.html",
        {"form": form, "exam": exam, "question": question, "page_title": "Add Choice"},
    )


@teacher_required
def teacher_choice_edit(request, exam_id, question_id, choice_id):
    exam = get_object_or_404(Exam, id=exam_id, teacher=request.user)
    question = get_object_or_404(Question, id=question_id, exam=exam)
    choice = get_object_or_404(Choice, id=choice_id, question=question)
    if request.method == "POST":
        form = ChoiceForm(request.POST, instance=choice)
        if form.is_valid():
            form.save()
            messages.success(request, "Choice updated.")
            return redirect("teacher_choice_list", exam_id=exam.id, question_id=question.id)
    else:
        form = ChoiceForm(instance=choice)

    return render(
        request,
        "teacher_portal/choice_form.html",
        {"form": form, "exam": exam, "question": question, "page_title": "Edit Choice"},
    )


@teacher_required
def teacher_choice_delete(request, exam_id, question_id, choice_id):
    exam = get_object_or_404(Exam, id=exam_id, teacher=request.user)
    question = get_object_or_404(Question, id=question_id, exam=exam)
    choice = get_object_or_404(Choice, id=choice_id, question=question)
    if request.method == "POST":
        choice.delete()
        messages.success(request, "Choice deleted.")
        return redirect("teacher_choice_list", exam_id=exam.id, question_id=question.id)
    return render(
        request,
        "teacher_portal/choice_delete.html",
        {"exam": exam, "question": question, "choice": choice},
    )


@teacher_required
def teacher_exam_enrollments(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id, teacher=request.user)
    enrollments = exam.enrollments.select_related("student")
    if request.method == "POST":
        form = ExamEnrollmentForm(request.POST)
        if form.is_valid():
            student = form.cleaned_data["student"]
            _, created = ExamEnrollment.objects.get_or_create(exam=exam, student=student)
            if created:
                messages.success(request, "Student enrolled.")
            else:
                messages.info(request, "Student is already enrolled.")
            return redirect("teacher_exam_enrollments", exam_id=exam.id)
    else:
        form = ExamEnrollmentForm()
    return render(
        request,
        "teacher_portal/enrollment_list.html",
        {"exam": exam, "enrollments": enrollments, "form": form},
    )


@teacher_required
def teacher_enrollment_delete(request, exam_id, enrollment_id):
    exam = get_object_or_404(Exam, id=exam_id, teacher=request.user)
    enrollment = get_object_or_404(ExamEnrollment, id=enrollment_id, exam=exam)
    if request.method == "POST":
        enrollment.delete()
        messages.success(request, "Enrollment removed.")
        return redirect("teacher_exam_enrollments", exam_id=exam.id)
    return render(request, "teacher_portal/enrollment_delete.html", {"exam": exam, "enrollment": enrollment})


@teacher_required
def teacher_results(request):
    exam_id = request.GET.get("exam")
    results = ExamResult.objects.filter(exam__teacher=request.user).select_related("student", "exam")
    exams = Exam.objects.filter(teacher=request.user)
    if exam_id:
        results = results.filter(exam_id=exam_id)
    return render(
        request,
        "teacher_portal/results.html",
        {"results": results, "exams": exams, "selected_exam": exam_id},
    )


@teacher_required
def teacher_exam_result_report(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id, teacher=request.user)
    results = exam.results.select_related("student")
    summary = results.aggregate(avg_score=Avg("score"), max_score=Max("score"), min_score=Min("score"), total=Count("id"))
    return render(
        request,
        "teacher_portal/exam_result_report.html",
        {"exam": exam, "results": results, "summary": summary},
    )


@teacher_required
def teacher_proctoring_logs(request):
    exam_id = request.GET.get("exam")
    flagged_only = request.GET.get("flagged") == "1"
    logs = ProctoringLog.objects.filter(exam__teacher=request.user).select_related("student", "exam")
    exams = Exam.objects.filter(teacher=request.user)
    if exam_id:
        logs = logs.filter(exam_id=exam_id)
    if flagged_only:
        logs = logs.filter(is_flagged=True)
    return render(
        request,
        "teacher_portal/proctoring_logs.html",
        {"logs": logs, "exams": exams, "selected_exam": exam_id, "flagged_only": flagged_only},
    )


@teacher_required
def teacher_proctoring_log_create(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id, teacher=request.user)
    if request.method == "POST":
        form = ProctoringLogForm(request.POST, exam=exam)
        if form.is_valid():
            log = form.save(commit=False)
            log.exam = exam
            log.save()
            messages.success(request, "Proctoring event logged.")
            return redirect("teacher_proctoring_logs")
    else:
        form = ProctoringLogForm(exam=exam)
    return render(request, "teacher_portal/proctoring_log_form.html", {"form": form, "exam": exam})


@teacher_required
def teacher_analytics(request):
    exam_stats = (
        Exam.objects.filter(teacher=request.user)
        .annotate(
            enrolled_count=Count("enrollments", distinct=True),
            submissions=Count("results", distinct=True),
            avg_score=Avg("results__score"),
            flagged_count=Count("proctoring_logs", filter=Q(proctoring_logs__is_flagged=True), distinct=True),
        )
        .order_by("-created_at")
    )
    return render(request, "teacher_portal/analytics.html", {"exam_stats": exam_stats})


@teacher_required
def teacher_export_results_csv(request):
    results = ExamResult.objects.filter(exam__teacher=request.user).select_related("student", "exam")
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="teacher_exam_results.csv"'
    writer = csv.writer(response)
    writer.writerow(["Exam", "Student", "Score", "Submitted At"])
    for row in results:
        writer.writerow([row.exam.title, row.student.username, row.score, row.submitted_at])
    return response


@teacher_required
def teacher_export_proctoring_csv(request):
    logs = ProctoringLog.objects.filter(exam__teacher=request.user).select_related("exam", "student")
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="teacher_proctoring_logs.csv"'
    writer = csv.writer(response)
    writer.writerow(["Exam", "Student", "Event", "Severity", "Flagged", "Created At", "Details"])
    for row in logs:
        writer.writerow(
            [
                row.exam.title,
                row.student.username if row.student else "-",
                row.event_type,
                row.severity,
                "Yes" if row.is_flagged else "No",
                row.created_at,
                row.details,
            ]
        )
    return response
