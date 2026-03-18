from django import forms
from django.contrib.auth.models import User

from accounts.models import UserProfile
from exams.models import Choice, Exam, ExamEnrollment, Question
from proctoring.models import ProctoringLog


class ExamForm(forms.ModelForm):
    class Meta:
        model = Exam
        fields = ("subject", "title", "duration_minutes", "total_marks", "scheduled_at", "deadline_at")
        widgets = {
            "scheduled_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "deadline_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            css_class = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = f"{css_class} form-control".strip()

    def clean(self):
        cleaned_data = super().clean()
        scheduled_at = cleaned_data.get("scheduled_at")
        deadline_at = cleaned_data.get("deadline_at")

        if scheduled_at and deadline_at and deadline_at <= scheduled_at:
            self.add_error("deadline_at", "Deadline must be after the exam start time.")

        return cleaned_data


class QuestionForm(forms.ModelForm):
    options = forms.CharField(
        required=False,
        widget=forms.HiddenInput(),
        help_text="For multiple choice: enter one option per line.",
    )
    correct_option = forms.ChoiceField(required=False, choices=())

    class Meta:
        model = Question
        fields = ("text", "question_type", "marks", "correct_answer")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            css_class = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = f"{css_class} form-control".strip()
        self.fields["correct_option"].widget.attrs["class"] = "form-control"

        if self.is_bound:
            posted_type = self.data.get("question_type")
            posted_options = [line.strip() for line in (self.data.get("options") or "").splitlines() if line.strip()]
            if posted_type == Question.QuestionType.MULTIPLE_CHOICE:
                self.fields["correct_option"].choices = [
                    (str(idx), f"Option {idx + 1}") for idx, _ in enumerate(posted_options)
                ]

        if self.instance and self.instance.pk and self.instance.question_type == Question.QuestionType.MULTIPLE_CHOICE:
            existing_choices = list(self.instance.choices.all())
            self.fields["options"].initial = "\n".join(choice.text for choice in existing_choices)
            option_choices = [(str(idx), f"Option {idx + 1}") for idx, _ in enumerate(existing_choices)]
            self.fields["correct_option"].choices = option_choices
            correct_idx = next((idx for idx, c in enumerate(existing_choices) if c.is_correct), None)
            if correct_idx is not None:
                self.fields["correct_option"].initial = str(correct_idx)

    def clean(self):
        cleaned_data = super().clean()
        question_type = cleaned_data.get("question_type")
        correct_answer = (cleaned_data.get("correct_answer") or "").strip()
        options_raw = cleaned_data.get("options") or ""
        options = [line.strip() for line in options_raw.splitlines() if line.strip()]
        correct_option = cleaned_data.get("correct_option")

        if question_type == Question.QuestionType.MULTIPLE_CHOICE:
            if len(options) < 2:
                self.add_error("options", "Add at least two options for a multiple-choice question.")
            if correct_option in (None, ""):
                self.add_error("correct_option", "Select which option is correct.")
            else:
                try:
                    selected_idx = int(correct_option)
                    if selected_idx < 0 or selected_idx >= len(options):
                        self.add_error("correct_option", "Selected correct option is out of range.")
                except (TypeError, ValueError):
                    self.add_error("correct_option", "Invalid correct option.")
            cleaned_data["correct_answer"] = ""

        if question_type == Question.QuestionType.THEORY and not correct_answer:
            self.add_error("correct_answer", "Provide the model/correct answer for theory questions.")

        cleaned_data["parsed_options"] = options
        return cleaned_data


class ChoiceForm(forms.ModelForm):
    class Meta:
        model = Choice
        fields = ("text", "is_correct")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["text"].widget.attrs["class"] = "form-control"
        self.fields["is_correct"].widget.attrs["class"] = "form-check-input"


class ExamEnrollmentForm(forms.ModelForm):
    class Meta:
        model = ExamEnrollment
        fields = ("student",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["student"].widget.attrs["class"] = "form-control"
        self.fields["student"].queryset = User.objects.filter(profile__role=UserProfile.Role.STUDENT)


class ProctoringLogForm(forms.ModelForm):
    class Meta:
        model = ProctoringLog
        fields = ("student", "event_type", "details", "severity", "is_flagged")

    def __init__(self, *args, **kwargs):
        exam = kwargs.pop("exam", None)
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            css_class = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = f"{css_class} form-control".strip()
        self.fields["is_flagged"].widget.attrs["class"] = "form-check-input"
        if exam:
            self.fields["student"].queryset = User.objects.filter(
                exam_enrollments__exam=exam,
                profile__role=UserProfile.Role.STUDENT,
            ).distinct()
