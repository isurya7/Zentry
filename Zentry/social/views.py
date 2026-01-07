from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Count, Q
from django.utils import timezone
from .models import AchievementPost, PostComment, UserReport
from accounts.models import UserProfile
from notifications.models import Notification

@login_required
def leaderboard(request):
    """Points leaderboard"""
    # Weekly leaderboard
    today = timezone.now().date()
    start_of_week = today - timezone.timedelta(days=today.weekday())
    
    weekly_leaders = UserProfile.objects.filter(
        weekly_points__gt=0
    ).order_by('-weekly_points')[:10]
    
    # All-time leaderboard
    all_time_leaders = UserProfile.objects.filter(
        total_points__gt=0
    ).order_by('-total_points')[:10]
    
    # Current user's rank
    user_profile = request.user.userprofile
    weekly_rank = UserProfile.objects.filter(weekly_points__gt=user_profile.weekly_points).count() + 1
    all_time_rank = UserProfile.objects.filter(total_points__gt=user_profile.total_points).count() + 1
    
    return render(request, 'social/leaderboard.html', {
        'weekly_leaders': weekly_leaders,
        'all_time_leaders': all_time_leaders,
        'user_profile': user_profile,
        'weekly_rank': weekly_rank,
        'all_time_rank': all_time_rank,
        'title': 'Leaderboard'
    })

@login_required
def feed(request):
    """Social feed showing achievement posts"""
    # Get posts from friends and public posts
    profile = request.user.userprofile
    friends = profile.friends.all()
    friend_users = [f.user for f in friends]
    
    posts = AchievementPost.objects.filter(
        Q(user__in=friend_users) | Q(is_public=True)
    ).exclude(user=request.user).select_related('user').prefetch_related('likes', 'comments')
    
    # User's own posts
    my_posts = AchievementPost.objects.filter(user=request.user)
    
    all_posts = (posts | my_posts).distinct().order_by('-created_at')[:50]
    
    return render(request, 'social/feed.html', {
        'posts': all_posts,
        'title': 'Feed'
    })

@login_required
def create_achievement_post(request):
    """Create a new achievement post"""
    if request.method == 'POST':
        title = request.POST.get('title', '')
        content = request.POST.get('content', '')
        achievement_type = request.POST.get('achievement_type', 'custom')
        points = int(request.POST.get('points', 0))
        
        post = AchievementPost.objects.create(
            user=request.user,
            title=title,
            content=content,
            achievement_type=achievement_type,
            points_earned=points,
            is_public=request.POST.get('is_public', 'on') == 'on'
        )
        
        if 'image' in request.FILES:
            post.image = request.FILES['image']
            post.save()
        
        messages.success(request, 'Achievement posted!')
        return redirect('social:feed')
    
    return render(request, 'social/create_post.html', {
        'title': 'Share Achievement'
    })

@login_required
def like_post(request, post_id):
    """Like/unlike a post"""
    post = get_object_or_404(AchievementPost, id=post_id)
    
    if request.user in post.likes.all():
        post.likes.remove(request.user)
        liked = False
    else:
        post.likes.add(request.user)
        liked = True
        
        # Notify post owner
        if post.user != request.user:
            try:
                Notification.objects.create(
                    recipient=post.user,
                    title=f"{request.user.username} liked your post",
                    message=f"{request.user.username} liked your achievement: {post.title}",
                    notification_type='achievement',
                    link=f'/social/feed/'
                )
            except:
                pass
    
    return JsonResponse({
        'liked': liked,
        'likes_count': post.likes.count()
    })

@login_required
def comment_post(request, post_id):
    """Add comment to a post"""
    if request.method == 'POST':
        post = get_object_or_404(AchievementPost, id=post_id)
        content = request.POST.get('content', '').strip()
        
        if content:
            comment = PostComment.objects.create(
                post=post,
                user=request.user,
                content=content
            )
            
            # Notify post owner
            if post.user != request.user:
                try:
                    Notification.objects.create(
                        recipient=post.user,
                        title=f"{request.user.username} commented on your post",
                        message=content[:100],
                        notification_type='achievement',
                        link=f'/social/feed/'
                    )
                except:
                    pass
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'comment': {
                        'id': comment.id,
                        'content': comment.content,
                        'user': comment.user.username,
                        'timestamp': comment.created_at.isoformat(),
                    }
                })
            messages.success(request, 'Comment added!')
    
    return redirect('social:feed')

@login_required
def report_user(request, user_id):
    """Report a user"""
    from django.contrib.auth.models import User
    
    if request.method == 'POST':
        reported_user = get_object_or_404(User, id=user_id)
        reason = request.POST.get('reason', '')
        description = request.POST.get('description', '')
        
        if reason and description:
            UserReport.objects.create(
                reporter=request.user,
                reported_user=reported_user,
                reason=reason,
                description=description
            )
            messages.success(request, 'User reported. Thank you for keeping the community safe.')
            return redirect('accounts:profile')
        else:
            messages.error(request, 'Please provide a reason and description.')
    
    return render(request, 'social/report_user.html', {
        'reported_user_id': user_id,
        'title': 'Report User'
    })

