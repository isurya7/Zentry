# Generated manually to migrate from Vision to VisionBoard
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
from django.utils import timezone


def migrate_vision_to_visionboard(apps, schema_editor):
    """Migrate data from Vision to VisionBoard"""
    Vision = apps.get_model('visionboard', 'Vision')
    VisionBoard = apps.get_model('visionboard', 'VisionBoard')
    
    # Copy data from Vision to VisionBoard
    for vision in Vision.objects.all():
        VisionBoard.objects.create(
            id=vision.id,
            user=vision.user,
            title=vision.content[:200] if vision.content else 'Untitled Vision',
            description=vision.content or '',
            cover_image=vision.image,
            points=20,  # Default points
            status='achieved' if vision.is_achieved else 'active',
            is_public=vision.is_public,
            created_at=vision.created_at,
            achieved_at=vision.achieved_at if vision.is_achieved else None,
        )


def reverse_migration(apps, schema_editor):
    """Reverse migration - copy data back to Vision"""
    Vision = apps.get_model('visionboard', 'Vision')
    VisionBoard = apps.get_model('visionboard', 'VisionBoard')
    
    for vision_board in VisionBoard.objects.all():
        Vision.objects.create(
            id=vision_board.id,
            user=vision_board.user,
            content=vision_board.description or vision_board.title,
            image=vision_board.cover_image,
            is_achieved=(vision_board.status == 'achieved'),
            is_public=vision_board.is_public,
            created_at=vision_board.created_at,
            achieved_at=vision_board.achieved_at,
        )


class Migration(migrations.Migration):

    dependencies = [
        ('visionboard', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # Step 1: Create VisionBoard model with all new fields
        migrations.CreateModel(
            name='VisionBoard',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200)),
                ('description', models.TextField()),
                ('cover_image', models.ImageField(blank=True, null=True, upload_to='visions/')),
                ('points', models.IntegerField(default=20)),
                ('status', models.CharField(choices=[('draft', 'Draft'), ('active', 'Active'), ('achieved', 'Achieved')], default='draft', max_length=20)),
                ('is_public', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('achieved_at', models.DateTimeField(blank=True, null=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='vision_boards', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        
        # Step 2: Create Checkpoint model
        migrations.CreateModel(
            name='Checkpoint',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200)),
                ('description', models.TextField(blank=True)),
                ('completed', models.BooleanField(default=False)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('order', models.IntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('vision_board', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='checkpoints', to='visionboard.visionboard')),
            ],
            options={
                'ordering': ['order', 'created_at'],
                'unique_together': {('vision_board', 'order')},
            },
        ),
        
        # Step 3: Add created_at to VisionReaction
        migrations.AddField(
            model_name='visionreaction',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, null=True),
        ),
        
        # Step 4: Rename timestamp to created_at in VisionComment (before adding new field)
        migrations.RenameField(
            model_name='visioncomment',
            old_name='timestamp',
            new_name='created_at',
        ),
        
        # Step 5: Migrate data from Vision to VisionBoard
        migrations.RunPython(migrate_vision_to_visionboard, reverse_migration),
        
        # Step 6: Update VisionReaction foreign key
        migrations.AlterField(
            model_name='visionreaction',
            name='vision',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reactions', to='visionboard.visionboard'),
        ),
        migrations.RenameField(
            model_name='visionreaction',
            old_name='vision',
            new_name='vision_board',
        ),
        
        # Step 7: Update VisionComment foreign key
        migrations.AlterField(
            model_name='visioncomment',
            name='vision',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='comments', to='visionboard.visionboard'),
        ),
        migrations.RenameField(
            model_name='visioncomment',
            old_name='vision',
            new_name='vision_board',
        ),
        
        # Step 8: Remove old Vision model
        migrations.DeleteModel(
            name='Vision',
        ),
    ]

