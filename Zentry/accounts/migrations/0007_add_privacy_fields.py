# accounts/migrations/0002_add_privacy_fields.py
from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='show_journals_publicly',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='show_points_publicly',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='show_visions_publicly',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='subscription_type',
            field=models.CharField(choices=[('free', 'Free'), ('pro', 'Pro'), ('premium', 'Premium')], default='free', max_length=20),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='subscription_ends',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='max_daily_tasks',
            field=models.IntegerField(default=5),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='daily_tasks_count',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='last_task_reset',
            field=models.DateField(default=django.utils.timezone.now),
        ),
    ]