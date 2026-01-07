from django.apps import AppConfig
from django.db.models.signals import post_save

class TasksConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'tasks'
    
    def ready(self):
        import tasks.signals