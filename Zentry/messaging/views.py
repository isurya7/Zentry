from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseForbidden
from django.contrib import messages
from django.db.models import Q
from django.utils import timezone
from .models import Conversation, Message
from accounts.models import UserProfile
from notifications.models import Notification

@login_required
def conversation_list(request):
    """List all conversations for the user"""
    conversations = Conversation.objects.filter(participants=request.user)
    
    # Get unread counts for each conversation
    conversation_data = []
    for conv in conversations:
        unread_count = Message.objects.filter(
            conversation=conv,
            is_read=False
        ).exclude(sender=request.user).count()
        
        other_user = conv.get_other_user(request.user)
        last_message = conv.messages.last()
        
        conversation_data.append({
            'conversation': conv,
            'other_user': other_user,
            'unread_count': unread_count,
            'last_message': last_message,
        })
    
    return render(request, 'messaging/conversations.html', {
        'conversations': conversation_data,
        'title': 'Messages'
    })

@login_required
def view_conversation(request, conversation_id):
    """View a specific conversation"""
    conversation = get_object_or_404(Conversation, id=conversation_id, participants=request.user)
    other_user = conversation.get_other_user(request.user)
    
    # Mark messages as read
    Message.objects.filter(
        conversation=conversation,
        is_read=False
    ).exclude(sender=request.user).update(is_read=True)
    
    messages = conversation.messages.all()
    
    return render(request, 'messaging/conversation.html', {
        'conversation': conversation,
        'other_user': other_user,
        'messages': messages,
        'title': f'Chat with {other_user.username}'
    })

@login_required
def start_conversation(request, user_id):
    """Start a new conversation with a user"""
    from django.contrib.auth.models import User
    
    other_user = get_object_or_404(User, id=user_id)
    
    # Check if users are friends
    profile = request.user.userprofile
    other_profile = other_user.userprofile
    
    if other_profile not in profile.friends.all():
        messages.error(request, 'You can only message your friends.')
        return redirect('accounts:profile')
    
    # Check if conversation already exists
    conversation = Conversation.objects.filter(
        participants=request.user
    ).filter(participants=other_user).first()
    
    if not conversation:
        conversation = Conversation.objects.create()
        conversation.participants.add(request.user, other_user)
    
    return redirect('messaging:conversation', conversation_id=conversation.id)

@login_required
def send_message(request, conversation_id):
    """Send a message in a conversation"""
    if request.method == 'POST':
        conversation = get_object_or_404(Conversation, id=conversation_id, participants=request.user)
        text = request.POST.get('text', '').strip()
        
        if text:
            message = Message.objects.create(
                conversation=conversation,
                sender=request.user,
                text=text
            )
            
            # Create notification for recipient
            other_user = conversation.get_other_user(request.user)
            try:
                Notification.objects.create(
                    recipient=other_user,
                    title=f"New message from {request.user.username}",
                    message=text[:100],
                    notification_type='message',
                    link=f'/chat/conversation/{conversation.id}/'
                )
            except:
                pass  # Notifications might not be migrated yet
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': {
                        'id': message.id,
                        'text': message.text,
                        'sender': message.sender.username,
                        'timestamp': message.timestamp.isoformat(),
                    }
                })
            messages.success(request, 'Message sent!')
        else:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': 'Message cannot be empty'}, status=400)
            messages.error(request, 'Message cannot be empty.')
    
    return redirect('messaging:conversation', conversation_id=conversation_id)

@login_required
def get_messages(request, conversation_id):
    """API endpoint to get messages (for AJAX)"""
    conversation = get_object_or_404(Conversation, id=conversation_id, participants=request.user)
    
    messages = conversation.messages.all()
    messages_data = [{
        'id': msg.id,
        'text': msg.text,
        'sender': msg.sender.username,
        'sender_id': msg.sender.id,
        'is_read': msg.is_read,
        'timestamp': msg.timestamp.isoformat(),
    } for msg in messages]
    
    return JsonResponse({'messages': messages_data})
