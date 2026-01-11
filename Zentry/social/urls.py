from django.urls import path
from . import views

app_name = 'social'

urlpatterns = [
    path('leaderboard/', views.leaderboard, name='leaderboard'),
    path('feed/', views.feed, name='feed'),
    path('post/create/', views.create_achievement_post, name='create_post'),
    path('post/<int:post_id>/like/', views.like_post, name='like_post'),
    path('post/<int:post_id>/comment/', views.comment_post, name='comment_post'),
    path('report/<int:user_id>/', views.report_user, name='report_user'),
    
    # New enhanced URLs
    path('post/<int:post_id>/share/', views.share_post, name='share_post'),
    path('post/<int:post_id>/edit/', views.edit_post, name='edit_post'),
    path('post/<int:post_id>/delete/', views.delete_post, name='delete_post'),
    path('post/<int:post_id>/report/', views.report_post, name='report_post'),
    path('post/<int:post_id>/comments/', views.get_post_comments, name='get_comments'),
    path('comment/<int:comment_id>/like/', views.like_comment, name='like_comment'),
    path('comment/<int:comment_id>/delete/', views.delete_comment, name='delete_comment'),
    path('hashtag/<str:hashtag>/', views.hashtag_feed, name='hashtag_feed'),
    path('auto-share/<str:achievement_type>/<int:object_id>/', 
         views.auto_share_achievement, name='auto_share_achievement'),
]


