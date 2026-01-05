import os
import base64
import re
import json
import logging
from datetime import datetime, timedelta
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import google.generativeai as genai
from django.conf import settings
from django.core.cache import cache

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Gmail OAuth constants
CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/emails/oauth2callback/")

SCOPES = ['https://www.googleapis.com/auth/gmail.modify']

# Configure Gemini API
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
    except Exception as e:
        logging.error(f"Error configuring Gemini API: {str(e)}")

logger = logging.getLogger(__name__)

def get_flow():
    """Create Google OAuth2.0 flow"""
    return Flow.from_client_config(
        {
            "web": {
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "redirect_uris": [REDIRECT_URI],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token"
            }
        },
        scopes=SCOPES
    )

def save_credentials(session, credentials):
    """Save user's OAuth credentials in session"""
    print("=== SAVE_CREDENTIALS ===")
    try:
        session["credentials"] = {
            "token": credentials.token,
            "refresh_token": credentials.refresh_token,
            "token_uri": credentials.token_uri,
            "client_id": credentials.client_id,
            "client_secret": credentials.client_secret,
            "scopes": credentials.scopes,
        }
        session.modified = True
        print("✅ Credentials saved to session successfully")
        print(f"Session keys after save: {list(session.keys())}")
    except Exception as e:
        print(f"❌ Error saving credentials: {e}")
        raise

def load_credentials(session):
    """Load user's OAuth credentials from session"""
    print("=== LOAD_CREDENTIALS ===")
    if "credentials" not in session:
        print("❌ No credentials found in session")
        return None
    
    print("✅ Credentials found in session")
    creds_data = session["credentials"]
    try:
        credentials = Credentials(
            token=creds_data["token"],
            refresh_token=creds_data.get("refresh_token"),
            token_uri=creds_data["token_uri"],
            client_id=creds_data["client_id"],
            client_secret=creds_data["client_secret"],
            scopes=creds_data["scopes"],
        )
        print("✅ Credentials loaded successfully")
        return credentials
    except Exception as e:
        print(f"❌ Error loading credentials: {e}")
        return None

def build_gmail_service(credentials):
    """Build Gmail API client"""
    try:
        return build("gmail", "v1", credentials=credentials, cache_discovery=False)
    except Exception as e:
        logger.error(f"Error building Gmail service: {str(e)}")
        raise

def is_spam_email(subject, sender, snippet):
    """Manual spam detection as fallback"""
    spam_indicators = [
        r'viagra', r'cialis', r'loan', r'mortgage', r'casino', r'lottery',
        r'winner', r'prize', r'free.*money', r'investment', r'opportunity',
        r'earn.*from.*home', r'work.*from.*home', r'financial.*freedom',
        r'guaranteed', r'risk.*free', r'million', r'billion', r'profit',
        r'discount', r'clearance', r'sale', r'limited.*time', r'act.*now',
        r'urgent', r'important.*message', r'account.*update', r'security.*alert',
        r'password.*reset', r'verify.*account', r'suspicious.*activity',
        r'nigerian.*prince', r'inheritance', r'unclaimed.*funds'
    ]
    
    # Check sender domain
    suspicious_domains = [
        '.ru', '.xyz', '.top', '.club', '.info', '.biz', '.online'
    ]
    
    content = f"{subject} {snippet}".lower()
    sender_lower = sender.lower()
    
    # Skip common mailing lists and notifications
    safe_senders = ['twitter', 'github', 'linkedin', 'facebook', 'instagram', 'amazon', 'ebay']
    for safe_sender in safe_senders:
        if safe_sender in sender_lower:
            return False
    
    # Check for spam indicators
    for pattern in spam_indicators:
        if re.search(pattern, content, re.IGNORECASE):
            return True
    
    # Check sender domain
    for domain in suspicious_domains:
        if domain in sender_lower:
            return True
    
    return False

def manual_importance_analysis(subject, snippet):
    """Manual importance analysis as fallback for Gemini"""
    important_keywords = [
        'urgent', 'important', 'meeting', 'deadline', 'project', 'report',
        'review', 'approval', 'action required', 'response needed', 'asap',
        'critical', 'priority', 'time-sensitive', 'confidential', 'follow up',
        'discussion', 'presentation', 'budget', 'financial', 'contract'
    ]
    
    work_related = [
        'work', 'team', 'company', 'client', 'customer', 'business',
        'project', 'task', 'assignment', 'deliverable', 'milestone',
        'manager', 'director', 'ceo', 'cto', 'meeting', 'conference'
    ]
    
    content = f"{subject} {snippet}".lower()
    
    # Check for importance indicators
    important_count = sum(1 for keyword in important_keywords if keyword in content)
    if important_count >= 2:
        return True
    
    # Check if it's work-related with multiple keywords
    work_keyword_count = sum(1 for keyword in work_related if keyword in content)
    if work_keyword_count >= 3:
        return True
    
    return False

def analyze_email_importance(subject, snippet):
    """Use Gemini to classify if email is important"""
    if not GEMINI_API_KEY:
        return manual_importance_analysis(subject, snippet)
    
    try:
        prompt = f"""
        Analyze this email and determine if it's important (work-related, urgent, requires action).
        Subject: {subject}
        Preview: {snippet}
        
        Respond with ONLY: IMPORTANT or NORMAL
        """
        
        model = genai.GenerativeModel("gemini-pro")
        response = model.generate_content(prompt)
        return "IMPORTANT" in response.text.upper()
        
    except Exception as e:
        logger.error(f"Gemini API error: {str(e)}")
        return manual_importance_analysis(subject, snippet)

def extract_name_from_email(email_string):
    """Extract name from email string"""
    try:
        # Pattern: "Name <email@domain.com>" or "email@domain.com"
        match = re.match(r'"?([^"<]+)"?\s*<[^>]+>', email_string)
        if match:
            return match.group(1).strip()
        
        # Extract from email address
        email_match = re.match(r'([^@]+)@', email_string)
        if email_match:
            name_part = email_match.group(1)
            # Convert to title case and replace dots with spaces
            name_part = name_part.replace('.', ' ').replace('_', ' ').title()
            return name_part
            
        return email_string.split('@')[0]
    except:
        return email_string

def format_email_date(date_string):
    """Format email date nicely with better error handling"""
    try:
        from email.utils import parsedate_to_datetime
        dt = parsedate_to_datetime(date_string)
        now = datetime.now()
        
        if dt.date() == now.date():
            return dt.strftime("Today %I:%M %p")
        elif dt.date() == (now - timedelta(days=1)).date():
            return dt.strftime("Yesterday %I:%M %p")
        elif dt.year == now.year:
            return dt.strftime("%b %d %I:%M %p")
        else:
            return dt.strftime("%b %d, %Y")
    except:
        # Return original string if parsing fails
        return date_string

def enhanced_fetch_emails(service, max_results=50):
    """Enhanced email fetching with fallback and spam filtering"""
    try:
        results = service.users().messages().list(
            userId="me", 
            maxResults=max_results,
            labelIds=['INBOX']
        ).execute()
        
        messages = results.get("messages", [])
        emails = []

        for msg in messages:
            try:
                msg_data = service.users().messages().get(
                    userId="me", 
                    id=msg["id"],
                    format='metadata',
                    metadataHeaders=['Subject', 'From', 'Date']
                ).execute()
                
                payload = msg_data.get("payload", {})
                headers = payload.get("headers", [])
                
                subject, sender, date = "No Subject", "Unknown", ""
                for header in headers:
                    if header["name"] == "Subject":
                        subject = header["value"]
                    if header["name"] == "From":
                        sender = header["value"]
                    if header["name"] == "Date":
                        date = header["value"]

                snippet = msg_data.get("snippet", "")
                
                # Skip spam emails
                if is_spam_email(subject, sender, snippet):
                    continue
                
                # Analyze importance
                is_important = analyze_email_importance(subject, snippet)

                emails.append({
                    "id": msg["id"],
                    "subject": subject,
                    "sender": sender,
                    "sender_name": extract_name_from_email(sender),
                    "snippet": snippet,
                    "date": format_email_date(date),
                    "is_important": is_important,
                    "read": 'UNREAD' not in msg_data.get('labelIds', [])
                })
                
            except Exception as e:
                logger.error(f"Error processing email {msg['id']}: {str(e)}")
                continue
                
        # Cache the emails for fallback
        cache.set('cached_emails', emails, timeout=300)  # 5 minutes
        return emails
        
    except Exception as e:
        logger.error(f"Error fetching emails: {str(e)}")
        # Return cached emails if available
        return get_cached_emails()

def get_cached_emails():
    """Get cached emails as fallback"""
    return cache.get('cached_emails', [])

def get_email_details(service, email_id):
    """Get detailed email information"""
    try:
        msg_data = service.users().messages().get(
            userId="me", 
            id=email_id, 
            format='full'
        ).execute()
        
        payload = msg_data.get("payload", {})
        headers = payload.get("headers", [])
        
        email_details = {
            "id": email_id,
            "subject": "No Subject",
            "sender": "Unknown",
            "sender_name": "Unknown",
            "date": "",
            "body": "",
            "attachments": []
        }
        
        for header in headers:
            if header["name"] == "Subject":
                email_details["subject"] = header["value"]
            if header["name"] == "From":
                email_details["sender"] = header["value"]
                email_details["sender_name"] = extract_name_from_email(header["value"])
            if header["name"] == "Date":
                email_details["date"] = format_email_date(header["value"])
        
        # Extract email body
        if 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain' and 'data' in part['body']:
                    data = part['body']['data']
                    email_details["body"] = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                    break
                elif part['mimeType'] == 'text/html' and 'data' in part['body']:
                    data = part['body']['data']
                    email_details["body"] = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
        elif 'body' in payload and 'data' in payload['body']:
            data = payload['body']['data']
            email_details["body"] = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
        
        # Extract attachments
        if 'parts' in payload:
            for part in payload['parts']:
                if part['filename'] and part['filename'] != '':
                    email_details["attachments"].append({
                        "filename": part['filename'],
                        "mimeType": part['mimeType'],
                        "size": part['body'].get('size', 0)
                    })
        
        return email_details
        
    except Exception as e:
        logger.error(f"Error getting email details: {str(e)}")
        # Return basic email info as fallback
        return {
            "id": email_id,
            "subject": "Email unavailable",
            "sender": "Unknown",
            "sender_name": "Unknown",
            "date": "",
            "body": "Could not load email content. Please try again later.",
            "attachments": []
        }

def send_reply(service, msg_id, to, subject, message_text):
    """Send reply to Gmail email"""
    try:
        raw_message = f"To: {to}\r\nSubject: Re: {subject}\r\n\r\n{message_text}"
        encoded_message = base64.urlsafe_b64encode(raw_message.encode("utf-8")).decode("utf-8")
        
        return service.users().messages().send(
            userId="me", 
            body={"raw": encoded_message, "threadId": msg_id}
        ).execute()
    except Exception as e:
        logger.error(f"Error sending reply: {str(e)}")
        raise

def store_reply_locally(user, email_id, to, subject, body):
    """Store email reply locally when API fails"""
    try:
        # Store in cache (in real app, use database)
        reply_data = {
            "user_id": user.id,
            "email_id": email_id,
            "to": to,
            "subject": subject,
            "body": body,
            "timestamp": datetime.now().isoformat()
        }
        
        # Get existing replies or create new list
        replies = cache.get(f'user_{user.id}_replies', [])
        replies.append(reply_data)
        cache.set(f'user_{user.id}_replies', replies, timeout=86400)  # 24 hours
        
        logger.info(f"Stored local reply: {user.username} -> {to}")
        
    except Exception as e:
        logger.error(f"Error storing local reply: {str(e)}")