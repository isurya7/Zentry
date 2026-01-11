# social/migrations/0002_enhance_models.py
from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('social', '0001_initial'),  # Your existing migration
    ]

    operations = [
        # Add tags field to AchievementPost
        migrations.AddField(
            model_name='achievementpost',
            name='tags',
            field=models.CharField(blank=True, max_length=500),
        ),
        
        # Add default value to achievement_type
        migrations.AlterField(
            model_name='achievementpost',
            name='achievement_type',
            field=models.CharField(
                choices=[
                    ('task', 'Task Completed'),
                    ('journal', 'Journal Entry'),
                    ('streak', 'Streak Milestone'),
                    ('points', 'Points Milestone'),
                    ('vision', 'Vision Achieved'),
                    ('custom', 'Custom Achievement'),
                ],
                default='custom',
                max_length=50
            ),
        ),
        
        # Add likes field to PostComment
        migrations.AddField(
            model_name='postcomment',
            name='likes',
            field=models.ManyToManyField(
                blank=True,
                related_name='liked_comments',
                to='auth.User'
            ),
        ),
        
        # Create PostShare model
        migrations.CreateModel(
            name='PostShare',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('shared_at', models.DateTimeField(auto_now_add=True)),
                ('comment', models.TextField(blank=True)),
                ('original_post', models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='shares', to='social.achievementpost')),
                ('user', models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='shared_posts', to='auth.User')),
            ],
            options={
                'ordering': ['-shared_at'],
            },
        ),
    ]