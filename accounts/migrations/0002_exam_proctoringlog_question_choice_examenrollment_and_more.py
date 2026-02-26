# Refactor compatibility migration.
# This intentionally keeps the previous migration name so environments that
# already recorded this migration don't break when syncing the refactor.

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = []
