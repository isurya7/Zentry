# Generated manually
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0005_userprofile_current_streak_userprofile_daily_points_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='last_point_award_date',
            field=models.DateField(blank=True, null=True),
        ),
    ]

