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
def profile_view(request):
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
    tasks_count = 0  
    tasks = []
    visions = []
    friends = profile.friends.all()
    
    # Get pending friend requests
    pending_requests = FriendRequest.objects.filter(to_user=profile, status='pending')
    
    return render(request, 'accounts/profile.html', {
        'form': form, 
        'profile': profile,
        'friends_count': friends_count,
        'tasks_count': tasks_count,
        'tasks': tasks,
        'visions': visions,
        'friends': friends,
        'pending_requests': pending_requests
    })

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