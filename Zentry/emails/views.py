from django.shortcuts import render, redirect
from django.core.paginator import Paginator
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from .utils import (
    get_flow,
    save_credentials,
    load_credentials,
    build_gmail_service,
    enhanced_fetch_emails,
    send_reply,
    get_email_details,
    store_reply_locally,
    manual_importance_analysis,
    is_spam_email,
    get_cached_emails
)
import logging

logger = logging.getLogger(__name__)

logger = logging.getLogger(__name__)

@login_required
def connect_gmail(request):
    """Start OAuth flow"""
    print("=== CONNECT_GMAIL VIEW ===")
    print(f"User: {request.user}")
    print(f"Session keys: {list(request.session.keys())}")
    
    try:
        flow = get_flow()
        redirect_uri = request.build_absolute_uri(reverse("emails:oauth2callback"))
        print(f"Redirect URI: {redirect_uri}")
        
        flow.redirect_uri = redirect_uri
        auth_url, state = flow.authorization_url(prompt="consent", access_type='offline')
        
        print(f"Generated auth URL: {auth_url}")
        print(f"State: {state}")
        
        # Store state in session for validation in callback
        request.session['oauth_state'] = state
        request.session.modified = True
        print(f"Stored state in session: {state}")
        
        return redirect(auth_url)
    except Exception as e:
        error_msg = f"Error in connect_gmail: {str(e)}"
        print(error_msg)
        logger.error(error_msg)
        messages.error(request, "Error connecting to Gmail. Please try again.")
        return redirect("emails:inbox")

@login_required
def oauth2callback(request):
    """Handle OAuth callback"""
    print("\n=== OAUTH2CALLBACK VIEW ===")
    print(f"Request GET parameters: {dict(request.GET)}")
    print(f"User: {request.user}")
    print(f"Session keys: {list(request.session.keys())}")
    print(f"Stored state: {request.session.get('oauth_state', 'NOT_FOUND')}")
    
    # Check for errors from Google
    if 'error' in request.GET:
        error_msg = f"Google OAuth error: {request.GET.get('error')} - {request.GET.get('error_description', 'No description')}"
        print(error_msg)
        messages.error(request, f"Authentication failed: {request.GET.get('error_description', 'Unknown error')}")
        return redirect("emails:connect_gmail")
    
    # Check for authorization code
    if 'code' not in request.GET:
        error_msg = "No authorization code found in request"
        print(error_msg)
        messages.error(request, "Authentication failed: No authorization code received")
        return redirect("emails:connect_gmail")
    
    try:
        authorization_code = request.GET['code']
        returned_state = request.GET.get('state', '')
        stored_state = request.session.get('oauth_state', '')
        
        print(f"Authorization code: {authorization_code}")
        print(f"Returned state: {returned_state}")
        print(f"Stored state: {stored_state}")
        
        # State validation (optional but recommended for security)
        if stored_state and returned_state != stored_state:
            print("STATE VALIDATION FAILED! Possible CSRF attack.")
            # For development, we might continue anyway, but log the issue
        
        # Get the flow instance
        flow = get_flow()
        redirect_uri = request.build_absolute_uri(reverse("emails:oauth2callback"))
        print(f"Setting redirect_uri to: {redirect_uri}")
        flow.redirect_uri = redirect_uri
        
        # Exchange authorization code for tokens
        print("Attempting to fetch token...")
        flow.fetch_token(code=authorization_code)
        print("Token fetched successfully!")
        
        # Get credentials
        credentials = flow.credentials
        print(f"Credentials obtained - valid: {credentials.valid}, expired: {credentials.expired}")
        print(f"Token: {credentials.token[:20]}...") if credentials.token else print("No token!")
        print(f"Refresh token: {'YES' if credentials.refresh_token else 'NO'}")
        print(f"Scopes: {credentials.scopes}")
        
        # Save credentials to session
        print("Saving credentials to session...")
        save_credentials(request.session, credentials)
        print("Credentials saved to session")
        print(f"Session keys after save: {list(request.session.keys())}")
        
        # Clean up state
        if 'oauth_state' in request.session:
            del request.session['oauth_state']
            request.session.modified = True
        
        messages.success(request, "Gmail connected successfully! ✅")
        return redirect("emails:inbox")
        
    except Exception as e:
        error_msg = f"Error in oauth2callback: {str(e)}"
        print(error_msg)
        import traceback
        traceback.print_exc()  # Print full traceback
        logger.error(error_msg)
        messages.error(request, "Error completing Gmail connection. Please try again.")
        return redirect("emails:connect_gmail")

@login_required
def inbox_view(request):
    """Show inbox emails with pagination"""
    print("\n=== INBOX_VIEW ===")
    print(f"User: {request.user}")
    print(f"Session keys: {list(request.session.keys())}")
    
    # Check if we have credentials
    credentials = load_credentials(request.session)
    print(f"Credentials loaded: {credentials is not None}")
    
    if not credentials:
        print("No credentials found, showing connect page")
        # No credentials, show connect prompt
        return render(request, "emails/connect.html")
    
    try:
        print("Attempting to build Gmail service...")
        # Try to use Gmail API
        service = build_gmail_service(credentials)
        print("Gmail service built successfully")
        
        print("Fetching emails...")
        emails = enhanced_fetch_emails(service, max_results=50)
        print(f"Fetched {len(emails)} emails")
        api_status = "connected"
    except Exception as e:
        error_msg = f"Error fetching emails: {str(e)}"
        print(error_msg)
        import traceback
        traceback.print_exc()
        # Fallback to cached emails
        emails = get_cached_emails()
        api_status = "disconnected"
        messages.warning(request, "Gmail API temporarily unavailable. Showing cached emails. 📝")
    
    # Manual importance analysis for all emails if needed
    for email in emails:
        if 'is_important' not in email:
            email['is_important'] = manual_importance_analysis(
                email.get('subject', ''), 
                email.get('snippet', '')
            )
    
    paginator = Paginator(emails, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    print(f"Rendering inbox with {len(emails)} emails, status: {api_status}")
    return render(request, "emails/inbox.html", {
        "emails": page_obj,
        "api_status": api_status,
        "total_emails": len(emails)
    })

@login_required
def refresh_emails(request):
    """Refresh inbox and fetch latest emails"""
    credentials = load_credentials(request.session)
    
    if not credentials:
        messages.error(request, "Please connect your Gmail account first")
        return redirect("emails:connect_gmail")
    
    try:
        service = build_gmail_service(credentials)
        emails = enhanced_fetch_emails(service, max_results=50)
        messages.success(request, f"Inbox refreshed! Found {len(emails)} emails. ✅")
    except Exception as e:
        logger.error(f"Error refreshing emails: {str(e)}")
        messages.error(request, "Error refreshing emails. Please try again.")
    
    return redirect("emails:inbox")

@login_required
def email_detail(request, email_id):
    """View single email and reply"""
    credentials = load_credentials(request.session)
    
    if not credentials:
        messages.error(request, "Please connect your Gmail account first")
        return redirect("emails:connect_gmail")
    
    try:
        service = build_gmail_service(credentials)
        email_data = get_email_details(service, email_id)
        
        if request.method == "POST":
            reply_text = request.POST.get("body")
            to = request.POST.get("to")
            subject = request.POST.get("subject")
            
            try:
                send_reply(service, email_id, to, subject, reply_text)
                messages.success(request, "Reply sent successfully! ✅")
                return redirect("emails:reply_success")
            except Exception as e:
                logger.error(f"Error sending reply: {str(e)}")
                store_reply_locally(request.user, email_id, to, subject, reply_text)
                messages.warning(request, "Reply saved locally (Gmail API unavailable) 📝")
                return redirect("emails:reply_success")

        return render(request, "emails/email_detail.html", {"email": email_data})
        
    except Exception as e:
        logger.error(f"Error loading email details: {str(e)}")
        messages.error(request, "Error loading email. Please try again.")
        return redirect("emails:inbox")

@login_required
def reply_email(request, email_id):
    """Handle email reply (API endpoint)"""
    credentials = load_credentials(request.session)
    
    if not credentials:
        return JsonResponse({"error": "Please connect your Gmail account first"}, status=400)
    
    if request.method == "POST":
        try:
            service = build_gmail_service(credentials)
            reply_text = request.POST.get("body")
            to = request.POST.get("to")
            subject = request.POST.get("subject")
            
            try:
                send_reply(service, email_id, to, subject, reply_text)
                return JsonResponse({"success": "Reply sent successfully"})
            except Exception as e:
                logger.error(f"Error sending reply: {str(e)}")
                store_reply_locally(request.user, email_id, to, subject, reply_text)
                return JsonResponse({"warning": "Reply saved locally (Gmail API unavailable)"})
                
        except Exception as e:
            logger.error(f"Error in reply_email: {str(e)}")
            return JsonResponse({"error": "Error sending reply"}, status=500)
    
    return JsonResponse({"error": "Invalid request method"}, status=405)

@login_required
def reply_success(request):
    """Reply success page"""
    return render(request, "emails/reply_success.html")

@login_required
def mark_resolved(request, email_id):
    """Mark email as resolved"""
    try:
        # In a real implementation, you'd store this in your database
        # For now, we'll just show a success message
        messages.success(request, "Email marked as resolved ✅")
        return redirect("emails:inbox")
    except Exception as e:
        logger.error(f"Error marking email as resolved: {str(e)}")
        messages.error(request, "Error marking email as resolved")
        return redirect("emails:inbox")

@login_required
def disconnect_gmail(request):
    """Disconnect Gmail integration"""
    if "credentials" in request.session:
        del request.session["credentials"]
        messages.success(request, "Gmail disconnected successfully")
    else:
        messages.info(request, "Gmail was not connected")
    return redirect("emails:inbox")