from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Count, Q
from django.utils import timezone
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
import re
from datetime import timedelta
from .models import AchievementPost, PostComment, PostShare, UserReport
from accounts.models import UserProfile
from notifications.models import Notification


@login_required
def leaderboard(request):
    """Points leaderboard"""
    # Weekly leaderboard
    today = timezone.now().date()
    start_of_week = today - timedelta(days=today.weekday())
    
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
    """Main social feed with enhanced features"""
    profile = request.user.userprofile
    
    # Get posts from friends
    friends = profile.friends.all()
    friend_users = [f.user for f in friends]
    
    # Base queryset: friends' posts + public posts + your own posts
    posts = AchievementPost.objects.filter(
        Q(user__in=friend_users) | 
        Q(is_public=True) |
        Q(user=request.user)
    ).exclude(
        # Exclude posts from blocked users
        Q(user__userprofile__in=profile.blocked_users.all()) |
        Q(user__userprofile__blocked_users=profile)
    ).select_related('user', 'user__userprofile').prefetch_related('likes', 'comments').distinct()
    
    # Apply filters
    filter_type = request.GET.get('filter', 'all')
    if filter_type == 'friends':
        posts = posts.filter(user__in=friend_users)
    elif filter_type == 'popular':
        # Posts with most likes in last 7 days
        week_ago = timezone.now() - timedelta(days=7)
        posts = posts.filter(created_at__gte=week_ago).annotate(
            like_count=Count('likes')
        ).order_by('-like_count', '-created_at')
    elif filter_type == 'recent':
        posts = posts.order_by('-created_at')
    else:
        posts = posts.order_by('-created_at')
    
    # Pagination
    page = request.GET.get('page', 1)
    paginator = Paginator(posts, 20)
    
    try:
        posts_page = paginator.page(page)
    except PageNotAnInteger:
        posts_page = paginator.page(1)
    except EmptyPage:
        posts_page = paginator.page(paginator.num_pages)
    
    # Show posts with trending hashtags
    trending_posts = AchievementPost.objects.filter(
        is_public=True,
        created_at__gte=timezone.now() - timedelta(days=7)
    ).annotate(
        like_count=Count('likes'),
        comment_count=Count('comments')
    ).order_by('-like_count', '-created_at')[:5]
    
    # Get trending hashtags
    trending_tags = get_trending_tags()
    
    # Friend suggestions for sidebar
    friend_suggestions = get_friend_suggestions(request.user, limit=5)
    
    context = {
        'posts': posts_page,
        'filter': filter_type,
        'trending_posts': trending_posts,
        'trending_tags': trending_tags,
        'friend_suggestions': friend_suggestions,
        'title': 'Feed'
    }
    
    return render(request, 'social/feed.html', context)


def get_trending_tags():
    """Get trending hashtags from posts"""
    week_ago = timezone.now() - timedelta(days=7)
    
    # Get all tags from recent posts
    recent_posts = AchievementPost.objects.filter(
        created_at__gte=week_ago,
        is_public=True
    ).exclude(tags='')
    
    tag_counts = {}
    for post in recent_posts:
        for tag in post.get_tags_list():
            tag = tag.lower().strip()
            if tag.startswith('#'):
                tag = tag[1:]
            if tag:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
    
    # Sort by count and get top 10
    trending = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    
    return trending


def get_friend_suggestions(user, limit=5):
    """Get friend suggestions based on mutual friends"""
    profile = user.userprofile
    
    # Get users who are not friends, not blocked, and not yourself
    exclude_users = list(profile.friends.all()) + [profile]
    
    # Find users with mutual friends
    suggestions = []
    
    for friend in profile.friends.all():
        for friend_of_friend in friend.friends.all():
            if (friend_of_friend not in exclude_users and 
                friend_of_friend not in suggestions):
                
                # Calculate mutual friends count
                my_friends = set(profile.friends.all())
                their_friends = set(friend_of_friend.friends.all())
                mutual_count = len(my_friends.intersection(their_friends))
                
                # Check if already requested
                request_sent = False  # You'll need to implement FriendRequest check
                
                suggestions.append({
                    'profile': friend_of_friend,
                    'mutual_friends': mutual_count,
                    'request_sent': request_sent,
                })
    
    # Sort by mutual friends count
    suggestions.sort(key=lambda x: x['mutual_friends'], reverse=True)
    
    return suggestions[:limit]


@login_required
def create_achievement_post(request):
    """Create a new achievement post with hashtags"""
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        content = request.POST.get('content', '').strip()
        achievement_type = request.POST.get('achievement_type', 'custom')
        points = int(request.POST.get('points', 0))
        
        # Auto-extract hashtags from content
        hashtags = re.findall(r'#(\w+)', content)
        tags = ''
        if hashtags:
            tags_list = [f'#{tag}' for tag in set(hashtags)]
            tags = ','.join(tags_list)
        
        # Add manually entered tags
        manual_tags = request.POST.get('tags', '').strip()
        if manual_tags:
            if tags:
                tags += ',' + manual_tags
            else:
                tags = manual_tags
        
        if title and content:
            post = AchievementPost.objects.create(
                user=request.user,
                title=title,
                content=content,
                achievement_type=achievement_type,
                points_earned=points,
                tags=tags,
                is_public=request.POST.get('is_public', 'on') == 'on'
            )
            
            if 'image' in request.FILES:
                post.image = request.FILES['image']
                post.save()
            
            # Create notification for followers
            try:
                profile = request.user.userprofile
                for friend in profile.friends.all():
                    if friend.show_task_publicly:
                        Notification.objects.create(
                            recipient=friend.user,
                            title=f"{request.user.username} posted an achievement",
                            message=f"{title}",
                            notification_type='achievement',
                            link=f'/social/feed/#post-{post.id}'
                        )
            except:
                pass
            
            messages.success(request, 'Achievement posted!')
            return redirect('social:feed')
        else:
            messages.error(request, 'Title and content are required.')
    
    return render(request, 'social/create_post.html', {
        'title': 'Share Achievement'
    })


@login_required
def like_post(request, post_id):
    """Like/unlike a post"""
    post = get_object_or_404(AchievementPost, id=post_id)
    
    if request.method == 'POST':
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
                        message=f"{request.user.username} liked: {post.title}",
                        notification_type='like',
                        link=f'/social/feed/#post-{post.id}'
                    )
                except:
                    pass
        
        return JsonResponse({
            'liked': liked,
            'likes_count': post.likes.count(),
            'post_id': post.id
        })
    
    return JsonResponse({'error': 'Invalid request'}, status=400)


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
                        notification_type='comment',
                        link=f'/social/feed/#post-{post.id}'
                    )
                except:
                    pass
            
            return JsonResponse({
                'success': True,
                'comment': {
                    'id': comment.id,
                    'content': comment.content,
                    'user': comment.user.username,
                    'user_avatar': comment.user.userprofile.get_avatar_url() if hasattr(comment.user, 'userprofile') else '',
                    'timestamp': comment.created_at.isoformat(),
                    'like_count': 0
                }
            })
    
    return JsonResponse({'success': False}, status=400)


@login_required
def like_comment(request, comment_id):
    """Like or unlike a comment"""
    comment = get_object_or_404(PostComment, id=comment_id)
    
    if request.method == 'POST':
        if request.user in comment.likes.all():
            comment.likes.remove(request.user)
            liked = False
        else:
            comment.likes.add(request.user)
            liked = True
        
        return JsonResponse({
            'liked': liked,
            'likes_count': comment.likes.count(),
            'comment_id': comment.id
        })
    
    return JsonResponse({'error': 'Invalid request'}, status=400)


@login_required
def share_post(request, post_id):
    """Share a post to user's feed"""
    if request.method == 'POST':
        post = get_object_or_404(AchievementPost, id=post_id)
        comment = request.POST.get('comment', '').strip()
        
        # Check if already shared
        already_shared = PostShare.objects.filter(
            original_post=post,
            user=request.user
        ).exists()
        
        if not already_shared:
            share = PostShare.objects.create(
                original_post=post,
                user=request.user,
                comment=comment
            )
            
            # Create notification for original poster
            if post.user != request.user:
                try:
                    Notification.objects.create(
                        recipient=post.user,
                        title=f"{request.user.username} shared your post",
                        message=comment[:100] if comment else "Shared your post",
                        notification_type='share',
                        link=f'/social/feed/#post-{post.id}'
                    )
                except:
                    pass
            
            return JsonResponse({
                'success': True,
                'share_count': post.shares.count(),
                'message': 'Post shared successfully!'
            })
        else:
            return JsonResponse({
                'success': False,
                'message': 'You already shared this post'
            }, status=400)
    
    return JsonResponse({'success': False}, status=400)


@login_required
def hashtag_feed(request, hashtag):
    """Show posts with specific hashtag"""
    # Remove # if present
    if hashtag.startswith('#'):
        hashtag = hashtag[1:]
    
    posts = AchievementPost.objects.filter(
        Q(tags__icontains=f'#{hashtag}') | 
        Q(tags__icontains=f',#{hashtag},') |
        Q(tags__icontains=f',#{hashtag}') |
        Q(tags__icontains=f'#{hashtag},'),
        is_public=True
    ).select_related('user').prefetch_related('likes', 'comments').order_by('-created_at')
    
    # Pagination
    page = request.GET.get('page', 1)
    paginator = Paginator(posts, 20)
    
    try:
        posts_page = paginator.page(page)
    except PageNotAnInteger:
        posts_page = paginator.page(1)
    except EmptyPage:
        posts_page = paginator.page(paginator.num_pages)
    
    related_tags = get_related_tags(hashtag)
    
    return render(request, 'social/hashtag_feed.html', {
        'posts': posts_page,
        'hashtag': f'#{hashtag}',
        'related_tags': related_tags,
        'title': f'#{hashtag}'
    })


def get_related_tags(main_tag):
    """Get tags commonly used with main tag"""
    posts_with_tag = AchievementPost.objects.filter(
        Q(tags__icontains=f'#{main_tag}') |
        Q(tags__icontains=f',#{main_tag},') |
        Q(tags__icontains=f',#{main_tag}') |
        Q(tags__icontains=f'#{main_tag},')
    ).exclude(tags='')
    
    tag_counts = {}
    for post in posts_with_tag:
        for tag in post.get_tags_list():
            tag = tag.lower().strip()
            if tag.startswith('#'):
                tag = tag[1:]
            if tag and tag != main_tag:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
    
    # Get top 5 related tags
    related = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    
    return related


@login_required
def delete_post(request, post_id):
    """Delete a post"""
    post = get_object_or_404(AchievementPost, id=post_id, user=request.user)
    
    if request.method == 'POST':
        post.delete()
        messages.success(request, 'Post deleted successfully.')
        return redirect('social:feed')
    
    return render(request, 'social/confirm_delete_post.html', {
        'post': post,
        'title': 'Delete Post'
    })


@login_required
def edit_post(request, post_id):
    """Edit a post"""
    post = get_object_or_404(AchievementPost, id=post_id, user=request.user)
    
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        content = request.POST.get('content', '').strip()
        achievement_type = request.POST.get('achievement_type', post.achievement_type)
        tags = request.POST.get('tags', '').strip()
        
        if title and content:
            post.title = title
            post.content = content
            post.achievement_type = achievement_type
            post.tags = tags
            post.is_public = request.POST.get('is_public', 'on') == 'on'
            
            if 'image' in request.FILES:
                post.image = request.FILES['image']
            
            post.save()
            messages.success(request, 'Post updated successfully!')
            return redirect('social:feed')
        else:
            messages.error(request, 'Title and content are required.')
    
    return render(request, 'social/edit_post.html', {
        'post': post,
        'title': 'Edit Post'
    })


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


@login_required
def report_post(request, post_id):
    """Report a post"""
    post = get_object_or_404(AchievementPost, id=post_id)
    
    if request.method == 'POST':
        reason = request.POST.get('reason', '')
        description = request.POST.get('description', '')
        
        if reason and description:
            # Create a custom report for posts
            from django.db import models
            
            class PostReport(models.Model):
                reporter = models.ForeignKey(User, on_delete=models.CASCADE)
                reported_post = models.ForeignKey(AchievementPost, on_delete=models.CASCADE)
                reason = models.CharField(max_length=200)
                description = models.TextField()
                status = models.CharField(max_length=20, choices=[
                    ('pending', 'Pending'),
                    ('reviewed', 'Reviewed'),
                    ('resolved', 'Resolved'),
                ], default='pending')
                created_at = models.DateTimeField(auto_now_add=True)
            
            # You'll need to create this model first
            messages.success(request, 'Post reported. Thank you for keeping the community safe.')
            return redirect('social:feed')
        else:
            messages.error(request, 'Please provide a reason and description.')
    
    return render(request, 'social/report_post.html', {
        'post': post,
        'title': 'Report Post'
    })


@login_required
def get_post_comments(request, post_id):
    """Get comments for a post (AJAX endpoint)"""
    post = get_object_or_404(AchievementPost, id=post_id)
    comments = post.comments.all().order_by('-created_at')
    
    comments_data = []
    for comment in comments:
        comments_data.append({
            'id': comment.id,
            'content': comment.content,
            'user': comment.user.username,
            'user_avatar': comment.user.userprofile.get_avatar_url() if hasattr(comment.user, 'userprofile') else '',
            'timestamp': comment.created_at.isoformat(),
            'like_count': comment.likes.count(),
            'liked': request.user in comment.likes.all() if request.user.is_authenticated else False,
        })
    
    return JsonResponse({
        'comments': comments_data,
        'count': comments.count()
    })


@login_required
def delete_comment(request, comment_id):
    """Delete a comment"""
    comment = get_object_or_404(PostComment, id=comment_id, user=request.user)
    
    if request.method == 'POST':
        comment.delete()
        return JsonResponse({'success': True})
    
    return JsonResponse({'success': False}, status=400)


@login_required
def auto_share_achievement(request, achievement_type, object_id):
    """Automatically share an achievement to feed"""
    if achievement_type == 'task':
        from tasks.models import DailyTask
        task = get_object_or_404(DailyTask, id=object_id, creator=request.user)
        
        post = AchievementPost.objects.create(
            user=request.user,
            title=f"Completed: {task.title}",
            content=f"I just completed my task '{task.title}' and earned +1 point! 🎉",
            achievement_type='task',
            points_earned=1,
            is_public=True,
            tags='#task #productivity'
        )
        
    elif achievement_type == 'journal':
        from journal.models import JournalEntry
        journal = get_object_or_404(JournalEntry, id=object_id, user=request.user)
        
        post = AchievementPost.objects.create(
            user=request.user,
            title=f"Journal Entry: {journal.title}",
            content=f"I wrote a new journal entry '{journal.title}' and earned +5 points! 📝",
            achievement_type='journal',
            points_earned=5,
            is_public=journal.is_public,
            tags='#journal #writing'
        )
        
    elif achievement_type == 'vision':
        from visionboard.models import VisionBoard
        vision = get_object_or_404(VisionBoard, id=object_id, user=request.user)
        
        post = AchievementPost.objects.create(
            user=request.user,
            title=f"🎯 Vision Achieved: {vision.title}!",
            content=f"I achieved my vision '{vision.title}' and earned {vision.points} points!",
            achievement_type='vision',
            points_earned=vision.points,
            is_public=vision.is_public,
            tags='#vision #achievement'
        )
    
    messages.success(request, 'Achievement shared to feed!')
    return redirect('social:feed')