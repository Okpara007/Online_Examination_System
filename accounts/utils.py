def dashboard_url_for_user(user):
    profile = getattr(user, "profile", None)
    if not profile:
        return "index"
    if profile.is_teacher:
        return "teacher_dashboard"
    if profile.is_student:
        return "student_dashboard"
    return "index"
