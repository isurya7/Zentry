import re
import requests
import os
from django.conf import settings
from django.utils import timezone
from .models import DiscoveredWord, PointTransaction
from accounts.models import UserProfile
from accounts.models import UserProfile
from notifications.models import Notification


def get_word_meaning(word):
    """Get word meaning using Gemini API"""
    gemini_api_key = os.getenv('GEMINI_API_KEY')
    if not gemini_api_key:
        return None
    
    try:
        # Try using google-generativeai SDK first (preferred method)
        try:
            import google.generativeai as genai
            genai.configure(api_key=gemini_api_key)
            model = genai.GenerativeModel('gemini-pro')
            
            prompt = f"Provide a brief dictionary definition (1-2 sentences) for the word '{word}'. Only return the definition, nothing else."
            response = model.generate_content(prompt)
            
            if response.text:
                return response.text.strip()
        except ImportError:
            # Fallback to REST API if SDK not available
            pass
        
        # Fallback to REST API
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={gemini_api_key}"
        
        payload = {
            "contents": [{
                "parts": [{
                    "text": f"Provide a brief dictionary definition (1-2 sentences) for the word '{word}'. Only return the definition, nothing else."
                }]
            }]
        }
        
        headers = {
            'Content-Type': 'application/json'
        }
        
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if 'candidates' in data and len(data['candidates']) > 0:
                content = data['candidates'][0].get('content', {})
                parts = content.get('parts', [])
                if parts and 'text' in parts[0]:
                    return parts[0]['text'].strip()
        
        return None
    except Exception as e:
        print(f"Error fetching word meaning from Gemini: {e}")
        return None


def is_high_level_word(word):
    """Determine if a word is high-level (complex/uncommon)"""
    # Simple heuristic: words longer than 6 characters or containing specific patterns
    word_lower = word.lower()
    
    # Common words to exclude
    common_words = {
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
        'of', 'with', 'by', 'from', 'this', 'that', 'these', 'those', 'is',
        'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had',
        'do', 'does', 'did', 'will', 'would', 'should', 'could', 'may', 'might',
        'can', 'must', 'shall', 'say', 'said', 'says', 'go', 'went', 'gone',
        'get', 'got', 'make', 'made', 'know', 'knew', 'known', 'think', 'thought',
        'take', 'took', 'taken', 'see', 'saw', 'seen', 'come', 'came', 'look',
        'use', 'used', 'find', 'found', 'give', 'gave', 'given', 'tell', 'told',
        'work', 'worked', 'call', 'called', 'try', 'tried', 'ask', 'asked',
        'need', 'needed', 'feel', 'felt', 'become', 'became', 'leave', 'left',
        'put', 'set', 'help', 'show', 'move', 'play', 'turn', 'start', 'stop',
        'run', 'live', 'believe', 'bring', 'happen', 'write', 'sit', 'stand',
        'lose', 'pay', 'meet', 'include', 'continue', 'set', 'learn', 'change',
        'lead', 'understand', 'watch', 'follow', 'stop', 'create', 'speak',
        'read', 'spend', 'grow', 'open', 'walk', 'win', 'teach', 'offer',
        'remember', 'love', 'consider', 'appear', 'buy', 'wait', 'serve',
        'die', 'send', 'expect', 'build', 'stay', 'fall', 'cut', 'reach',
        'kill', 'raise', 'pass', 'sell', 'decide', 'return', 'explain',
        'hope', 'develop', 'carry', 'break', 'receive', 'agree', 'support',
        'hit', 'produce', 'eat', 'cover', 'catch', 'draw', 'choose'
    }
    
    # Exclude common words
    if word_lower in common_words:
        return False
    
    # High-level words are typically:
    # 1. Longer than 6 characters
    # 2. Contain specific prefixes/suffixes indicating complexity
    # 3. Have multiple syllables (rough heuristic: multiple vowels)
    
    if len(word) < 6:
        return False
    
    # Check for complex word patterns
    complex_patterns = [
        r'^[a-z]*(tion|sion|ance|ence|ment|ness|ity|ism|ology|graphy|phobia|philia)[a-z]*$',
        r'^[a-z]*(ous|ful|less|able|ible|ive|ary|ory|ical|ical)[a-z]*$',
    ]
    
    for pattern in complex_patterns:
        if re.match(pattern, word_lower):
            return True
    
    # Count vowels as proxy for syllables (rough heuristic)
    vowels = len(re.findall(r'[aeiou]', word_lower))
    if vowels >= 3:
        return True
    
    return False


def extract_and_analyze_words(content, user, journal_entry=None):
    """Extract words from journal content and analyze them"""
    # Extract words (4+ characters, alphabetical only)
    words = set(re.findall(r'\b[a-zA-Z]{4,}\b', content.lower()))
    
    discovered_words = []
    total_word_points = 0
    
    for word in words:
        # Check if word is already discovered by this user
        existing_word, created = DiscoveredWord.objects.get_or_create(
            user=user,
            word=word,
            defaults={
                'journal_entry': journal_entry,
                'discovered_date': timezone.now().date(),
                'is_high_level': False,
                'points_earned': 0,
            }
        )
        
        # Only process if it's a new discovery or we need to update meaning
        if created or not existing_word.meaning:
            # Check if it's a high-level word
            is_high_level = is_high_level_word(word)
            existing_word.is_high_level = is_high_level
            
            # Get meaning from Gemini API
            meaning = get_word_meaning(word)
            if meaning:
                existing_word.meaning = meaning
            
            # Award points for high-level words
            if is_high_level and created:
                existing_word.points_earned = 1
                total_word_points += 1
                
                # Create transaction record
                PointTransaction.objects.create(
                    user=user,
                    transaction_type='word_discovery',
                    points=1,
                    description=f"Discovered high-level word: {word}",
                    reference_id=journal_entry.id if journal_entry else None,
                )
            
            existing_word.journal_entry = journal_entry
            existing_word.save()
            discovered_words.append(existing_word)
    
    return discovered_words, total_word_points


def check_and_award_streak_bonus(user, current_streak, previous_streak=0):
    """Check if user reached a 10-day streak milestone and award bonus points"""
    streak_bonus_points = 0
    
    # Award +20 points when reaching exactly 10, 20, 30, etc. days
    # Only award if we just crossed a 10-day milestone (e.g., from 9 to 10, or 19 to 20)
    if current_streak > 0 and current_streak % 10 == 0:
        # Check if we just reached this milestone (previous streak was less)
        previous_milestone = (previous_streak // 10) * 10
        current_milestone = (current_streak // 10) * 10
        
        if current_milestone > previous_milestone:
            streak_bonus_points = 20
            
            # Create transaction record
            PointTransaction.objects.create(
                user=user,
                transaction_type='streak_milestone',
                points=streak_bonus_points,
                description=f"Reached {current_streak}-day journal streak milestone!",
            )
            
            # Create notification
            try:
                Notification.objects.create(
                    recipient=user,
                    title=f"🔥 {current_streak}-Day Streak Milestone!",
                    message=f"Congratulations! You've maintained a {current_streak}-day journal streak and earned +20 bonus points!",
                    notification_type='achievement',
                    link='/journal/'
                )
            except:
                pass
    
    return streak_bonus_points


def deduct_journal_points(user, journal_entry):
    """Deduct all points earned from a journal entry when it's deleted"""
    total_points = journal_entry.get_total_points_earned()
    
    if total_points > 0:
        # Update user profile
        profile = UserProfile.objects.get(user=user)
        profile.total_points = max(0, profile.total_points - total_points)
        profile.save()
        
        # Create transaction record for deduction
        PointTransaction.objects.create(
            user=user,
            transaction_type='journal_deleted',
            points=-total_points,
            description=f"Deleted journal entry: {journal_entry.title}",
            reference_id=journal_entry.id,
        )
        
        return total_points
    
    return 0
