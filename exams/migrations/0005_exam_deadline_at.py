from datetime import timedelta

from django.db import migrations, models
from django.utils import timezone


def set_deadline_for_existing_exams(apps, schema_editor):
    Exam = apps.get_model("exams", "Exam")
    now = timezone.now()
    for exam in Exam.objects.all().iterator():
        base_time = exam.scheduled_at or now
        duration = max(int(exam.duration_minutes or 0), 1)
        exam.deadline_at = base_time + timedelta(minutes=duration)
        exam.save(update_fields=["deadline_at"])


class Migration(migrations.Migration):

    dependencies = [
        ("exams", "0004_examresult_correct_count_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="exam",
            name="deadline_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.RunPython(set_deadline_for_existing_exams, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="exam",
            name="deadline_at",
            field=models.DateTimeField(),
        ),
    ]
