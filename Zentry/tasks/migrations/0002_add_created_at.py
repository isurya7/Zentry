# Generated manually to add created_at column to existing table

from django.db import migrations, models
import django.utils.timezone


def set_created_at(apps, schema_editor):
    """Set created_at for existing tasks"""
    DailyTask = apps.get_model('tasks', 'DailyTask')
    DailyTask.objects.all().update(created_at=django.utils.timezone.now())


class Migration(migrations.Migration):

    dependencies = [
        ('tasks', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='dailytask',
            name='created_at',
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
        migrations.RunPython(set_created_at, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='dailytask',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True),
        ),
    ]

