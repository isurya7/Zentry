from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponseForbidden
from django.db.models import Q, Max
from django.utils import timezone
from .models import VisionBoard, Checkpoint
from .forms import VisionBoardForm, CheckpointForm
from tasks.utils import award_points
from social.models import AchievementPost
from notifications.models import Notification

@login_required
def vision_list(request):
    """List all vision boards for the user"""
    # User's own vision boards
    my_visions = VisionBoard.objects.filter(user=request.user).order_by('-created_at')
    
    # Public vision boards from other users
    public_visions = VisionBoard.objects.filter(
        is_public=True,
        user__is_active=True
    ).exclude(user=request.user).select_related('user').order_by('-created_at')[:20]
    
    return render(request, 'visionboard/vision_list.html', {
        'my_visions': my_visions,
        'public_visions': public_visions,
        'title': 'Vision Boards'
    })

@login_required
def create_vision(request):
    """Create a new vision board"""
    if request.method == 'POST':
        form = VisionBoardForm(request.POST, request.FILES)
        if form.is_valid():
            vision = form.save(commit=False)
            vision.user = request.user
            vision.status = 'active'  # Set to active after creation
            vision.points = max(20, vision.points)  # Ensure minimum 20 points
            vision.save()
            
            messages.success(request, f'Vision board "{vision.title}" created successfully!')
            return redirect('visionboard:view_vision', vision_id=vision.id)
    else:
        form = VisionBoardForm()
    
    return render(request, 'visionboard/create_vision.html', {
        'form': form,
        'title': 'Create Vision Board'
    })

@login_required
def view_vision(request, vision_id):
    """View a vision board with its checkpoints"""
    vision = get_object_or_404(VisionBoard, id=vision_id)
    
    # Check if user has permission to view
    if not vision.is_public and vision.user != request.user:
        return HttpResponseForbidden("You don't have permission to view this vision board.")
    
    checkpoints = vision.checkpoints.all()
    progress = vision.get_progress_percentage()
    all_completed = vision.all_checkpoints_completed()
    
    # Check if user owns this vision
    is_owner = vision.user == request.user
    can_achieve = is_owner and vision.status != 'achieved' and all_completed
    
    return render(request, 'visionboard/view_vision.html', {
        'vision': vision,
        'checkpoints': checkpoints,
        'progress': progress,
        'all_completed': all_completed,
        'can_achieve': can_achieve,
        'is_owner': is_owner,
        'title': vision.title
    })

@login_required
def edit_vision(request, vision_id):
    """Edit a vision board (cannot delete)"""
    vision = get_object_or_404(VisionBoard, id=vision_id)
    
    # Only owner can edit
    if vision.user != request.user:
        return HttpResponseForbidden("You don't have permission to edit this vision board.")
    
    # Cannot edit if already achieved
    if vision.status == 'achieved':
        messages.warning(request, 'Cannot edit an achieved vision board.')
        return redirect('visionboard:view_vision', vision_id=vision.id)
    
    if request.method == 'POST':
        form = VisionBoardForm(request.POST, request.FILES, instance=vision)
        if form.is_valid():
            vision = form.save(commit=False)
            vision.points = max(20, vision.points)  # Ensure minimum 20 points
            vision.save()
            messages.success(request, 'Vision board updated successfully!')
            return redirect('visionboard:view_vision', vision_id=vision.id)
    else:
        form = VisionBoardForm(instance=vision)
    
    return render(request, 'visionboard/edit_vision.html', {
        'form': form,
        'vision': vision,
        'title': f'Edit {vision.title}'
    })

@login_required
def add_checkpoint(request, vision_id):
    """Add a checkpoint to a vision board"""
    vision = get_object_or_404(VisionBoard, id=vision_id)
    
    # Only owner can add checkpoints
    if vision.user != request.user:
        return HttpResponseForbidden("You don't have permission to add checkpoints.")
    
    if vision.status == 'achieved':
        messages.warning(request, 'Cannot add checkpoints to an achieved vision board.')
        return redirect('visionboard:view_vision', vision_id=vision.id)
    
    if request.method == 'POST':
        form = CheckpointForm(request.POST)
        if form.is_valid():
            checkpoint = form.save(commit=False)
            checkpoint.vision_board = vision
            checkpoint.save()
            messages.success(request, 'Checkpoint added successfully!')
            return redirect('visionboard:view_vision', vision_id=vision.id)
    else:
        # Set default order to next available
        max_order = vision.checkpoints.aggregate(Max('order'))['order__max'] or -1
        form = CheckpointForm(initial={'order': max_order + 1})
    
    return render(request, 'visionboard/add_checkpoint.html', {
        'form': form,
        'vision': vision,
        'title': f'Add Checkpoint - {vision.title}'
    })

@login_required
def mark_checkpoint_complete(request, checkpoint_id):
    """Mark a checkpoint as complete/incomplete"""
    checkpoint = get_object_or_404(Checkpoint, id=checkpoint_id)
    vision = checkpoint.vision_board
    
    # Only owner can mark checkpoints
    if vision.user != request.user:
        return HttpResponseForbidden("You don't have permission to modify checkpoints.")
    
    if vision.status == 'achieved':
        return JsonResponse({'error': 'Cannot modify checkpoints of an achieved vision board.'}, status=400)
    
    if request.method == 'POST':
        action = request.POST.get('action', 'complete')
        if action == 'complete':
            checkpoint.mark_complete()
            message = 'Checkpoint marked as complete!'
        else:
            checkpoint.mark_incomplete()
            message = 'Checkpoint marked as incomplete.'
        
        # Check if all checkpoints are now completed
        all_completed = vision.all_checkpoints_completed()
        
        return JsonResponse({
            'success': True,
            'message': message,
            'completed': checkpoint.completed,
            'all_completed': all_completed,
            'progress': vision.get_progress_percentage()
        })
    
    return JsonResponse({'error': 'Invalid request method.'}, status=400)

@login_required
def achieve_vision(request, vision_id):
    """Mark vision board as achieved and award points"""
    vision = get_object_or_404(VisionBoard, id=vision_id)
    
    # Only owner can achieve vision
    if vision.user != request.user:
        return HttpResponseForbidden("You don't have permission to achieve this vision board.")
    
    if vision.status == 'achieved':
        messages.info(request, 'This vision board is already achieved.')
        return redirect('visionboard:view_vision', vision_id=vision.id)
    
    # Check if all checkpoints are completed
    if not vision.all_checkpoints_completed():
        messages.warning(request, 'All checkpoints must be completed before achieving this vision board.')
        return redirect('visionboard:view_vision', vision_id=vision.id)
    
    if request.method == 'POST':
        vision.status = 'achieved'
        vision.achieved_at = timezone.now()
        vision.save()
        
        # Award points
        award_points(request.user, vision.points, activity_type='vision')
        
        # Create notification
        try:
            Notification.objects.create(
                recipient=request.user,
                title=f"🎯 Vision Achieved: {vision.title}!",
                message=f"Congratulations! You've achieved your vision and earned {vision.points} points!",
                notification_type='achievement',
                link=f'/vision/{vision.id}/'
            )
        except:
            pass
        
        messages.success(request, f'Congratulations! Vision board achieved! You earned {vision.points} points!')
        return redirect('visionboard:view_vision', vision_id=vision.id)
    
    # Calculate completed checkpoints count
    completed_count = vision.checkpoints.filter(completed=True).count()
    total_count = vision.checkpoints.count()
    
    return render(request, 'visionboard/confirm_achieve.html', {
        'vision': vision,
        'completed_count': completed_count,
        'total_count': total_count,
        'title': f'Achieve {vision.title}'
    })

@login_required
def post_to_feed(request, vision_id):
    """Post achieved vision board to social feed"""
    vision = get_object_or_404(VisionBoard, id=vision_id)
    
    # Only owner can post
    if vision.user != request.user:
        return HttpResponseForbidden("You don't have permission to post this vision board.")
    
    # Only achieved visions can be posted
    if vision.status != 'achieved':
        messages.warning(request, 'Only achieved vision boards can be posted to the feed.')
        return redirect('visionboard:view_vision', vision_id=vision.id)
    
    if request.method == 'POST':
        # Create achievement post
        post = AchievementPost.objects.create(
            user=request.user,
            title=f"🎯 Achieved Vision: {vision.title}",
            content=f"{vision.description}\n\nPoints earned: {vision.points}\nAchieved on: {vision.achieved_at.strftime('%B %d, %Y') if vision.achieved_at else 'Recently'}",
            image=vision.cover_image,
            points_earned=vision.points,
            achievement_type='custom',
            is_public=request.POST.get('is_public', 'on') == 'on'
        )
        
        messages.success(request, 'Vision board posted to feed!')
        return redirect('social:feed')
    
    return render(request, 'visionboard/post_to_feed.html', {
        'vision': vision,
        'title': f'Post {vision.title} to Feed'
    })

# Remove delete_vision function as visions cannot be deleted
