from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.utils import dashboard_url_for_user
from exams.models import Choice, ExamEnrollment, ExamResult, ExamSession, Question, StudentAnswer
from proctoring.models import ProctoringLog


def student_required(view_func):
    @wraps(view_func)
    @login_required
    def _wrapped(request, *args, **kwargs):
        profile = getattr(request.user, "profile", None)
        if not profile or not profile.is_student:
            messages.error(request, "You do not have access to the student portal.")
            return redirect(dashboard_url_for_user(request.user))
        return view_func(request, *args, **kwargs)

    return _wrapped


def _remaining_seconds(session):
    now = timezone.now()
    total_seconds = session.exam.duration_minutes * 60
    elapsed = int((now - session.started_at).total_seconds())
    remaining = max(0, total_seconds - elapsed)

    deadline_at = getattr(session.exam, "deadline_at", None)
    if deadline_at:
        remaining_until_deadline = max(0, int((deadline_at - now).total_seconds()))
        return min(remaining, remaining_until_deadline)
    return remaining


def _deadline_passed(exam, now=None):
    now = now or timezone.now()
    deadline_at = getattr(exam, "deadline_at", None)
    return bool(deadline_at and deadline_at <= now)


def _grade_and_submit_session(session, post_data, auto_submitted=False):
    questions = list(
        session.exam.questions.prefetch_related("choices").all()
    )
    score = 0
    correct_count = 0
    wrong_count = 0

    for question in questions:
        selected_choice = None
        selected_choice_id = None
        theory_answer = ""

        if question.question_type == Question.QuestionType.MULTIPLE_CHOICE:
            selected_choice_id = post_data.get(f"question_{question.id}_choice")
            if selected_choice_id:
                selected_choice = question.choices.filter(id=selected_choice_id).first()
        else:
            theory_answer = post_data.get(f"question_{question.id}_theory", "").strip()

        awarded = question.grade_answer(selected_choice_id=selected_choice_id, theory_answer=theory_answer)
        is_correct = awarded >= question.marks

        StudentAnswer.objects.update_or_create(
            session=session,
            question=question,
            defaults={
                "selected_choice": selected_choice,
                "theory_answer": theory_answer,
                "is_correct": is_correct,
                "awarded_marks": awarded,
            },
        )

        score += awarded
        if is_correct:
            correct_count += 1
        else:
            wrong_count += 1

    submitted_at = timezone.now()
    time_taken_seconds = int((submitted_at - session.started_at).total_seconds())

    result, _ = ExamResult.objects.update_or_create(
        exam=session.exam,
        student=session.student,
        defaults={
            "score": score,
            "correct_count": correct_count,
            "wrong_count": wrong_count,
            "total_questions": len(questions),
            "time_taken_seconds": max(0, time_taken_seconds),
            "submitted_at": submitted_at,
        },
    )

    session.submitted_at = submitted_at
    session.is_auto_submitted = auto_submitted
    if session.warning_count >= 3:
        session.is_flagged = True
    session.save(update_fields=["submitted_at", "is_auto_submitted", "is_flagged"])
    return result


@student_required
def student_dashboard(request):
    enrollments = (
        ExamEnrollment.objects.filter(student=request.user)
        .select_related("exam")
        .order_by("-enrolled_at")
    )
    results_by_exam = {
        result.exam_id: result
        for result in ExamResult.objects.filter(student=request.user)
    }
    now = timezone.now()
    exam_rows = []
    for enrollment in enrollments:
        exam = enrollment.exam
        result = results_by_exam.get(exam.id)
        is_scheduled = bool(exam.scheduled_at)
        is_closed = _deadline_passed(exam, now=now)
        can_start = ((not is_scheduled) or (exam.scheduled_at and exam.scheduled_at <= now)) and not is_closed
        exam_rows.append(
            {
                "exam": exam,
                "result": result,
                "can_start": can_start,
                "status": "Completed" if result else ("Closed" if is_closed else ("Available" if can_start else "Scheduled")),
            }
        )
    return render(
        request,
        "student_portal/dashboard.html",
        {"exam_rows": exam_rows, "current_time": timezone.localtime(timezone.now())},
    )


@student_required
def student_exam_start(request, exam_id):
    enrollment = get_object_or_404(
        ExamEnrollment.objects.select_related("exam"),
        exam_id=exam_id,
        student=request.user,
    )
    exam = enrollment.exam

    now = timezone.now()

    if exam.scheduled_at and exam.scheduled_at > now:
        messages.error(request, "This exam is not open yet.")
        return redirect("student_dashboard")
    if _deadline_passed(exam, now=now):
        messages.error(request, "Exam deadline has passed. You can no longer access this exam.")
        return redirect("student_dashboard")

    existing_result = ExamResult.objects.filter(exam=exam, student=request.user).first()
    if existing_result:
        messages.info(request, "You already submitted this exam. Showing your result.")
        return redirect("student_result_detail", result_id=existing_result.id)

    if request.method == "POST":
        if request.POST.get("proctor_consent") != "1":
            messages.error(request, "You must agree to the proctoring policy before starting the exam.")
            return render(
                request,
                "student_portal/exam_start.html",
                {"exam": exam, "current_time": timezone.localtime(timezone.now())},
            )

        face_probe = request.FILES.get("face_probe")
        profile = request.user.profile
        note = "Face verification simulated for project demo (matching checks bypassed)."

        # Simulation mode: keep the capture flow, store the latest probe image, and skip strict checks.
        if face_probe:
            profile.face_image = face_probe
            profile.save(update_fields=["face_image"])

        # Original strict verification flow intentionally disabled for this project simulation:
        # ok, note = verify_face_match(profile.face_image, face_probe)
        # if not ok:
        #     messages.error(request, f"Face verification failed: {note}")
        #     return render(
        #         request,
        #         "student_portal/exam_start.html",
        #         {"exam": exam, "current_time": timezone.localtime(timezone.now())},
        #     )

        session = (
            ExamSession.objects.filter(exam=exam, student=request.user, submitted_at__isnull=True)
            .order_by("-started_at")
            .first()
        )
        if not session:
            session = ExamSession.objects.create(
                exam=exam,
                student=request.user,
                face_verified=True,
                face_verification_note=note,
            )
        else:
            session.face_verified = True
            session.face_verification_note = note
            session.save(update_fields=["face_verified", "face_verification_note"])

        return redirect("student_take_exam", exam_id=exam.id)

    return render(
        request,
        "student_portal/exam_start.html",
        {"exam": exam, "current_time": timezone.localtime(timezone.now())},
    )


@student_required
def student_take_exam(request, exam_id):
    enrollment = get_object_or_404(ExamEnrollment, exam_id=exam_id, student=request.user)
    exam = enrollment.exam
    if _deadline_passed(exam):
        session = (
            ExamSession.objects.filter(exam=exam, student=request.user, submitted_at__isnull=True)
            .order_by("-started_at")
            .first()
        )
        if session:
            result = _grade_and_submit_session(session, post_data={}, auto_submitted=True)
            messages.warning(request, "Exam deadline reached. Your session was auto-submitted.")
            return redirect("student_result_detail", result_id=result.id)
        messages.error(request, "Exam deadline has passed. You can no longer access this exam.")
        return redirect("student_dashboard")

    session = (
        ExamSession.objects.filter(exam=exam, student=request.user, submitted_at__isnull=True)
        .order_by("-started_at")
        .first()
    )
    if not session:
        messages.error(request, "Start and verify exam first.")
        return redirect("student_exam_start", exam_id=exam.id)

    remaining_seconds = _remaining_seconds(session)
    if remaining_seconds <= 0:
        result = _grade_and_submit_session(session, post_data={}, auto_submitted=True)
        messages.warning(request, "Time ran out. Exam was auto-submitted.")
        return redirect("student_result_detail", result_id=result.id)

    questions = exam.questions.prefetch_related("choices")
    return render(
        request,
        "student_portal/take_exam.html",
        {
            "exam": exam,
            "session": session,
            "questions": questions,
            "remaining_seconds": remaining_seconds,
        },
    )


@student_required
@require_POST
def student_submit_exam(request, exam_id):
    enrollment = get_object_or_404(ExamEnrollment, exam_id=exam_id, student=request.user)
    exam = enrollment.exam
    session = (
        ExamSession.objects.filter(exam=exam, student=request.user, submitted_at__isnull=True)
        .order_by("-started_at")
        .first()
    )
    if not session:
        messages.error(request, "No active exam session found.")
        return redirect("student_dashboard")

    if _deadline_passed(exam):
        result = _grade_and_submit_session(session, post_data=request.POST, auto_submitted=True)
        messages.warning(request, "Deadline passed. Your exam was auto-submitted.")
        return redirect("student_result_detail", result_id=result.id)

    auto_submitted = request.POST.get("auto_submit") == "1" or _remaining_seconds(session) <= 0
    result = _grade_and_submit_session(session, post_data=request.POST, auto_submitted=auto_submitted)
    if auto_submitted:
        messages.warning(request, "Exam was auto-submitted.")
    else:
        messages.success(request, "Exam submitted successfully.")
    return redirect("student_result_detail", result_id=result.id)


@student_required
def student_results(request):
    results = ExamResult.objects.filter(student=request.user).select_related("exam").order_by("-submitted_at")
    return render(request, "student_portal/results.html", {"results": results})


@student_required
def student_result_detail(request, result_id):
    result = get_object_or_404(ExamResult.objects.select_related("exam"), id=result_id, student=request.user)
    session = (
        ExamSession.objects.filter(exam=result.exam, student=request.user, submitted_at__isnull=False)
        .order_by("-submitted_at")
        .first()
    )
    answers = []
    if session:
        answers = session.answers.select_related("question", "selected_choice").order_by("question__order")
    proctor_logs = ProctoringLog.objects.filter(exam=result.exam, student=request.user).order_by("-created_at")[:20]
    return render(
        request,
        "student_portal/result_detail.html",
        {
            "result": result,
            "session": session,
            "answers": answers,
            "proctor_logs": proctor_logs,
        },
    )


@student_required
@require_POST
def student_proctor_event(request, exam_id):
    session = (
        ExamSession.objects.filter(exam_id=exam_id, student=request.user, submitted_at__isnull=True)
        .order_by("-started_at")
        .first()
    )
    if not session:
        return JsonResponse({"ok": False, "error": "No active session."}, status=400)

    event_type = request.POST.get("event_type", "unknown")
    severity = request.POST.get("severity", ProctoringLog.Severity.LOW)
    details = request.POST.get("details", "")
    flagged = request.POST.get("flagged") == "1"

    if flagged or severity in {ProctoringLog.Severity.MEDIUM, ProctoringLog.Severity.HIGH}:
        session.warning_count += 1
    if session.warning_count >= 3:
        session.is_flagged = True
    session.save(update_fields=["warning_count", "is_flagged"])

    ProctoringLog.objects.create(
        exam_id=exam_id,
        student=request.user,
        event_type=event_type,
        details=details,
        severity=severity,
        is_flagged=flagged or session.warning_count >= 3,
    )
    return JsonResponse(
        {
            "ok": True,
            "warning_count": session.warning_count,
            "force_submit": session.warning_count >= 3,
        }
    )
