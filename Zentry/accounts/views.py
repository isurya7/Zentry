from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.db import IntegrityError
from .forms import SignUpForm, SignInForm, UserProfileForm, PasswordConfirmationForm, CombinedProfileForm
from .models import UserProfile, FriendRequest
from django.contrib.auth.models import User
from django.db.models import Q, Count
from journal.models import JournalEntry
from tasks.models import DailyTask
from visionboard.models import VisionBoard
from social.models import AchievementPost
from notifications.models import Notification

def signup_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard:dashboard')

    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            try:
                user = form.save()
                
                # Create user profile
                UserProfile.objects.create(user=user)
                
                # Log the user in
                login(request, user)
                messages.success(request, f'Account created successfully! Welcome to Zentry, {user.username}!')
                return redirect('dashboard:dashboard')
                
            except IntegrityError:
                messages.error(request, 'An error occurred during account creation. Please try again.')
        else:
            # Add more specific error messages
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = SignUpForm()

    return render(request, 'accounts/signup.html', {'form': form})

def signin_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard:dashboard')

    if request.method == 'POST':
        form = SignInForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            
            # Check if account is deactivated
            if user is not None:
                try:
                    profile = user.userprofile
                    if profile.is_deactivated:
                        messages.error(request, 'This account has been deactivated.')
                        return render(request, 'accounts/signin.html', {'form': form})
                except UserProfile.DoesNotExist:
                    # Create profile if it doesn't exist
                    UserProfile.objects.create(user=user)
                
                login(request, user)
                remember_me = form.cleaned_data.get('remember_me', False)
                if not remember_me:
                    # Session will expire when browser closes
                    request.session.set_expiry(0)
                
                messages.success(request, f'Welcome back, {user.username}!')
                return redirect('dashboard:dashboard')
            else:
                messages.error(request, 'Invalid username or password')
        else:
            messages.error(request, 'Invalid username or password')
    else:
        form = SignInForm()

    return render(request, 'accounts/signin.html', {'form': form})

@login_required
def logout_view(request):
    logout(request)
    messages.success(request, 'You have been successfully logged out.')
    return redirect('accounts:signin')

@login_required
def profile_view(request, username=None):
    """View profile - can be own or other user's"""
    if username:
        # Viewing another user's profile
        user = get_object_or_404(User, username=username)
        profile = get_object_or_404(UserProfile, user=user)
        
        # Check if blocked
        if profile in request.user.userprofile.blocked_users.all():
            messages.error(request, "You have blocked this user.")
            return redirect('dashboard:dashboard')
        
        # Check privacy settings
        can_view_profile = (
            profile.show_points_publicly or 
            profile.user in request.user.userprofile.friends.all()
        )
        
        if not can_view_profile:
            messages.error(request, "This profile is private.")
            return redirect('accounts:profile')
        
        # Calculate mutual friends
        mutual_friends = []
        if request.user != user:
            my_friends = set(request.user.userprofile.friends.all())
            their_friends = set(profile.friends.all())
            mutual_profiles = my_friends.intersection(their_friends)
            mutual_friends = list(mutual_profiles)
        
        # Get shared content
        shared_journals = []
        shared_visions = []
        
        if profile.show_journals_publicly or request.user.userprofile in profile.friends.all():
            shared_journals = JournalEntry.objects.filter(
                user=user,
                is_public=True
            ).order_by('-created_at')[:10]
        
        if profile.show_visions_publicly or request.user.userprofile in profile.friends.all():
            shared_visions = VisionBoard.objects.filter(
                user=user,
                is_public=True
            ).order_by('-created_at')[:10]
        
        # Get recent achievements
        recent_achievements = AchievementPost.objects.filter(
            user=user,
            is_public=True
        ).order_by('-created_at')[:5]
        
        # Check friendship status
        is_friend = profile in request.user.userprofile.friends.all()
        friend_request_sent = FriendRequest.objects.filter(
            from_user=request.user.userprofile,
            to_user=profile
        ).exists()
        friend_request_received = FriendRequest.objects.filter(
            from_user=profile,
            to_user=request.user.userprofile
        ).exists()
        
        # Get form for settings (only if viewing own profile)
        form = None
        
        context = {
            'viewed_user': user,
            'profile': profile,
            'is_own_profile': False,
            'is_friend': is_friend,
            'friend_request_sent': friend_request_sent,
            'friend_request_received': friend_request_received,
            'mutual_friends': mutual_friends,
            'mutual_count': len(mutual_friends),
            'can_see_points': profile.show_points_publicly or is_friend,
            'journals': shared_journals,
            'visions': shared_visions,
            'achievements': recent_achievements,
            'friends': profile.friends.all()[:9],  # Show first 9
            'friends_count': profile.friends.count(),
            'form': form,  # No form for other users
            'pending_requests': None,  # Only show own pending requests
            'title': f"{user.get_full_name() or user.username}'s Profile"
        }
        
    else:
        # Viewing own profile
        try:
            profile = request.user.userprofile
        except UserProfile.DoesNotExist:
            profile = UserProfile.objects.create(user=request.user)
        
        if request.method == 'POST':
            # Handle User model updates
            if 'first_name' in request.POST:
                request.user.first_name = request.POST['first_name']
            if 'last_name' in request.POST:
                request.user.last_name = request.POST['last_name']
            request.user.save()
            
            # Handle UserProfile updates
            form = UserProfileForm(request.POST, request.FILES, instance=profile)
            if form.is_valid():
                form.save()
                messages.success(request, 'Profile updated successfully!')
                return redirect('accounts:profile')
            else:
                messages.error(request, 'Please correct the errors below.')
        else:
            form = UserProfileForm(instance=profile)
        
        # Get counts for the profile page
        friends_count = profile.friends.count()
        
        # Get user's content
        tasks_count = DailyTask.objects.filter(creator=request.user).count()
        tasks = DailyTask.objects.filter(creator=request.user).order_by('-date')[:5]
        visions = VisionBoard.objects.filter(user=request.user).order_by('-created_at')[:5]
        journals = JournalEntry.objects.filter(user=request.user).order_by('-created_at')[:5]
        achievements = AchievementPost.objects.filter(user=request.user).order_by('-created_at')[:5]
        friends = profile.friends.all()[:9]
        
        # Get pending friend requests
        pending_requests = FriendRequest.objects.filter(to_user=profile, status='pending')
        
        context = {
            'viewed_user': request.user,
            'profile': profile,
            'is_own_profile': True,
            'is_friend': False,  # Can't be friend with yourself
            'friend_request_sent': False,
            'friend_request_received': False,
            'mutual_friends': [],
            'mutual_count': 0,
            'can_see_points': True,  # Always see own points
            'journals': journals,
            'visions': visions,
            'achievements': achievements,
            'tasks': tasks,
            'tasks_count': tasks_count,
            'friends': friends,
            'friends_count': friends_count,
            'form': form,
            'pending_requests': pending_requests,
            'title': 'My Profile'
        }
    
    return render(request, 'accounts/profile.html', context)

@login_required
def send_friend_request(request, user_id):
    if request.method == 'POST':
        try:
            to_user = User.objects.get(id=user_id)
            to_user_profile = to_user.userprofile
            from_user_profile = request.user.userprofile
            
            # Check if user is trying to add themselves
            if to_user_profile == from_user_profile:
                return JsonResponse({'error': 'You cannot send a friend request to yourself'}, status=400)
            
            # Check if user is blocked
            if to_user_profile in from_user_profile.blocked_users.all():
                return JsonResponse({'error': 'You cannot send friend requests to blocked users'}, status=400)
            
            if from_user_profile in to_user_profile.blocked_users.all():
                return JsonResponse({'error': 'This user has blocked you'}, status=400)
            
            # Check if already friends
            if to_user_profile in from_user_profile.friends.all():
                return JsonResponse({'error': 'You are already friends with this user'}, status=400)
            
            # Check if a friend request already exists
            if FriendRequest.objects.filter(
                from_user=from_user_profile, 
                to_user=to_user_profile
            ).exists():
                return JsonResponse({'error': 'Friend request already sent'}, status=400)
            
            # Check if there's a pending request in the opposite direction
            if FriendRequest.objects.filter(
                from_user=to_user_profile, 
                to_user=from_user_profile,
                status='pending'
            ).exists():
                # Auto-accept if the other user already sent a request
                existing_request = FriendRequest.objects.get(
                    from_user=to_user_profile, 
                    to_user=from_user_profile
                )
                existing_request.status = 'accepted'
                existing_request.save()
                
                # Add each other as friends
                from_user_profile.friends.add(to_user_profile)
                to_user_profile.friends.add(from_user_profile)
                
            # Create notification
            try:
                Notification.objects.create(
                    recipient=to_user_profile.user,
                    title=f"{from_user_profile.user.username} accepted your friend request",
                    message=f"You are now friends with {from_user_profile.user.username}!",
                    notification_type='friend_request',
                    link='/accounts/profile/'
                )
            except:
                pass
            
                return JsonResponse({'success': 'Friend request accepted automatically'})
            
            # Create friend request
            FriendRequest.objects.create(
                from_user=from_user_profile,
                to_user=to_user_profile,
                status='pending'
            )
            
            # Create notification
            try:
                Notification.objects.create(
                    recipient=to_user_profile.user,
                    title=f"{from_user_profile.user.username} sent you a friend request",
                    message=f"{from_user_profile.user.username} wants to be your friend",
                    notification_type='friend_request',
                    link='/accounts/profile/'
                )
            except:
                pass
            
            return JsonResponse({'success': 'Friend request sent'})
        except User.DoesNotExist:
            return JsonResponse({'error': 'User not found'}, status=404)
        except UserProfile.DoesNotExist:
            return JsonResponse({'error': 'User profile not found'}, status=404)
    
    return JsonResponse({'error': 'Invalid request method'}, status=405)

@login_required
def respond_friend_request(request, request_id):
    if request.method == 'POST':
        try:
            friend_request = FriendRequest.objects.get(id=request_id, to_user=request.user.userprofile)
            action = request.POST.get('action')
            
            if action == 'accept':
                friend_request.status = 'accepted'
                friend_request.save()
                # Add each other as friends
                friend_request.from_user.friends.add(friend_request.to_user)
                friend_request.to_user.friends.add(friend_request.from_user)
                
                # Create notification
                try:
                    Notification.objects.create(
                        recipient=friend_request.from_user.user,
                        title=f"{friend_request.to_user.user.username} accepted your friend request",
                        message=f"You are now friends with {friend_request.to_user.user.username}!",
                        notification_type='friend_request',
                        link='/accounts/profile/'
                    )
                except:
                    pass
                
                return JsonResponse({'success': 'Friend request accepted'})
            elif action == 'reject':
                friend_request.status = 'rejected'
                friend_request.save()
                return JsonResponse({'success': 'Friend request rejected'})
            else:
                return JsonResponse({'error': 'Invalid action'}, status=400)
        except FriendRequest.DoesNotExist:
            return JsonResponse({'error': 'Friend request not found'}, status=404)
    
    return JsonResponse({'error': 'Invalid request method'}, status=405)

@login_required
def block_user(request, user_id):
    if request.method == 'POST':
        try:
            user_to_block = User.objects.get(id=user_id)
            user_to_block_profile = user_to_block.userprofile
            current_user_profile = request.user.userprofile
            
            # Check if already blocked
            if user_to_block_profile in current_user_profile.blocked_users.all():
                return JsonResponse({'error': 'User is already blocked'}, status=400)
            
            # Block the user
            current_user_profile.blocked_users.add(user_to_block_profile)
            
            # Remove from friends if they are friends
            if user_to_block_profile in current_user_profile.friends.all():
                current_user_profile.friends.remove(user_to_block_profile)
                user_to_block_profile.friends.remove(current_user_profile)
            
            # Delete any pending friend requests
            FriendRequest.objects.filter(
                from_user=current_user_profile, 
                to_user=user_to_block_profile
            ).delete()
            
            FriendRequest.objects.filter(
                from_user=user_to_block_profile, 
                to_user=current_user_profile
            ).delete()
            
            return JsonResponse({'success': 'User blocked successfully'})
        except User.DoesNotExist:
            return JsonResponse({'error': 'User not found'}, status=404)
        except UserProfile.DoesNotExist:
            return JsonResponse({'error': 'User profile not found'}, status=404)
    
    return JsonResponse({'error': 'Invalid request method'}, status=405)

@login_required
def unblock_user(request, user_id):
    if request.method == 'POST':
        try:
            user_to_unblock = User.objects.get(id=user_id)
            user_to_unblock_profile = user_to_unblock.userprofile
            current_user_profile = request.user.userprofile
            
            # Check if user is actually blocked
            if user_to_unblock_profile not in current_user_profile.blocked_users.all():
                return JsonResponse({'error': 'User is not blocked'}, status=400)
            
            # Unblock the user
            current_user_profile.blocked_users.remove(user_to_unblock_profile)
            
            return JsonResponse({'success': 'User unblocked successfully'})
        except User.DoesNotExist:
            return JsonResponse({'error': 'User not found'}, status=404)
        except UserProfile.DoesNotExist:
            return JsonResponse({'error': 'User profile not found'}, status=404)
    
    return JsonResponse({'error': 'Invalid request method'}, status=405)

@login_required
def remove_friend(request, user_id):
    """Remove a friend"""
    if request.method == 'POST':
        try:
            friend = User.objects.get(id=user_id)
            friend_profile = friend.userprofile
            current_user_profile = request.user.userprofile
            
            # Remove from friends
            if friend_profile in current_user_profile.friends.all():
                current_user_profile.friends.remove(friend_profile)
                friend_profile.friends.remove(current_user_profile)
                return JsonResponse({'success': 'Friend removed successfully'})
            else:
                return JsonResponse({'error': 'User is not your friend'}, status=400)
        except User.DoesNotExist:
            return JsonResponse({'error': 'User not found'}, status=404)
    
    return JsonResponse({'error': 'Invalid request method'}, status=405)

@login_required
def report_user(request, user_id):
    """Report a user for inappropriate behavior"""
    from social.models import UserReport
    
    if request.method == 'POST':
        try:
            reported_user = User.objects.get(id=user_id)
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
        except User.DoesNotExist:
            messages.error(request, 'User not found.')
            return redirect('accounts:profile')
    
    reported_user = get_object_or_404(User, id=user_id)
    return render(request, 'accounts/report_user.html', {
        'reported_user': reported_user,
        'title': 'Report User'
    })

@login_required
def deactivate_account(request):
    if request.method == 'POST':
        form = PasswordConfirmationForm(request.user, request.POST)
        if form.is_valid():
            # Deactivate the account
            profile = request.user.userprofile
            profile.is_deactivated = True
            profile.deactivation_date = timezone.now()
            profile.save()
            
            # Logout the user
            logout(request)
            messages.success(request, 'Your account has been deactivated successfully.')
            return redirect('accounts:signin')
        else:
            messages.error(request, 'Invalid password. Please try again.')
    else:
        form = PasswordConfirmationForm(request.user)
    
    return render(request, 'accounts/deactivate_account.html', {'form': form})

@login_required
def delete_account(request):
    if request.method == 'POST':
        form = PasswordConfirmationForm(request.user, request.POST)
        if form.is_valid():
            # Delete the user account
            user = request.user
            logout(request)
            user.delete()
            messages.success(request, 'Your account has been permanently deleted.')
            return redirect('accounts:signin')
        else:
            messages.error(request, 'Invalid password. Please try again.')
    else:
        form = PasswordConfirmationForm(request.user)
    
    return render(request, 'accounts/delete_account.html', {'form': form})

@login_required
def global_search(request):
    """Integrated search system"""
    query = request.GET.get('q', '').strip()
    search_type = request.GET.get('type', 'all')
    
    results = {
        'users': [],
        'journals': [],
        'visions': [],
        'posts': [],
    }
    
    if query:
        current_profile = request.user.userprofile
        
        # Search Users (always available)
        if search_type in ['all', 'users']:
            user_results = UserProfile.objects.filter(
                Q(user__username__icontains=query) |
                Q(user__first_name__icontains=query) |
                Q(user__last_name__icontains=query),
                is_deactivated=False
            ).exclude(user=request.user).select_related('user')
            
            for profile in user_results:
                # Check friendship status
                is_friend = profile in current_profile.friends.all()
                friend_request_sent = FriendRequest.objects.filter(
                    from_user=current_profile,
                    to_user=profile
                ).exists()
                friend_request_received = FriendRequest.objects.filter(
                    from_user=profile,
                    to_user=current_profile
                ).exists()
                
                # Calculate mutual friends
                mutual_friends = 0
                if not is_friend:
                    my_friends = set(current_profile.friends.all())
                    their_friends = set(profile.friends.all())
                    mutual_friends = len(my_friends.intersection(their_friends))
                
                results['users'].append({
                    'profile': profile,
                    'is_friend': is_friend,
                    'friend_request_sent': friend_request_sent,
                    'friend_request_received': friend_request_received,
                    'mutual_friends': mutual_friends,
                    'can_see_points': profile.show_points_publicly or is_friend,
                })
        
        # Search Public Journals
        if search_type in ['all', 'journals']:
            journals = JournalEntry.objects.filter(
                Q(title__icontains=query) | 
                Q(content__icontains=query) |
                Q(tags__icontains=query),
                is_public=True
            ).select_related('user').order_by('-created_at')[:20]
            
            for journal in journals:
                results['journals'].append(journal)
        
        # Search Public Vision Boards
        if search_type in ['all', 'visions']:
            visions = VisionBoard.objects.filter(
                Q(title__icontains=query) |
                Q(description__icontains=query),
                is_public=True
            ).select_related('user').order_by('-created_at')[:20]
            
            for vision in visions:
                results['visions'].append(vision)
        
        # Search Public Posts
        if search_type in ['all', 'posts']:
            posts = AchievementPost.objects.filter(
                Q(title__icontains=query) |
                Q(content__icontains=query),
                is_public=True
            ).select_related('user').order_by('-created_at')[:20]
            
            for post in posts:
                results['posts'].append(post)
    
    # Get friend suggestions
    friend_suggestions = get_friend_suggestions(request.user)
    
    context = {
        'results': results,
        'query': query,
        'search_type': search_type,
        'friend_suggestions': friend_suggestions,
        'title': f'Search: {query}' if query else 'Search'
    }
    
    return render(request, 'accounts/search_results.html', context)


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
                request_sent = FriendRequest.objects.filter(
                    from_user=profile,
                    to_user=friend_of_friend
                ).exists()
                
                request_received = FriendRequest.objects.filter(
                    from_user=friend_of_friend,
                    to_user=profile
                ).exists()
                
                suggestions.append({
                    'profile': friend_of_friend,
                    'mutual_friends': mutual_count,
                    'request_sent': request_sent,
                    'request_received': request_received,
                })
    
    # Sort by mutual friends count
    suggestions.sort(key=lambda x: x['mutual_friends'], reverse=True)
    
    return suggestions[:limit]


@login_required
def friend_suggestions_view(request):
    """Page showing all friend suggestions"""
    suggestions = get_friend_suggestions(request.user, limit=20)
    
    return render(request, 'accounts/friend_suggestions.html', {
        'suggestions': suggestions,
        'title': 'Friend Suggestions'
    })

def public_profile_view(request, username):
    """Public profile view for other users"""
    user = get_object_or_404(User, username=username)
    profile = get_object_or_404(UserProfile, user=user)
    
    # Check if user is blocked
    if profile in request.user.userprofile.blocked_users.all():
        messages.error(request, "You have blocked this user.")
        return redirect('dashboard:dashboard')
    
    # Get public content
    public_journals = []
    if profile.show_journals_publicly:
        public_journals = JournalEntry.objects.filter(
            user=user,
            is_public=True
        ).order_by('-created_at')[:5]
    
    public_visions = []
    if profile.show_visions_publicly:
        public_visions = VisionBoard.objects.filter(
            user=user,
            is_public=True
        ).order_by('-created_at')[:5]
    
    public_achievements = AchievementPost.objects.filter(
        user=user,
        is_public=True
    ).order_by('-created_at')[:5]
    
    context = {
        'viewed_user': user,
        'profile': profile,
        'journals': public_journals,
        'visions': public_visions,
        'achievements': public_achievements,
        'title': f"{user.get_full_name() or user.username}'s Profile"
    }
    
    return render(request, 'accounts/public_profile.html', context)