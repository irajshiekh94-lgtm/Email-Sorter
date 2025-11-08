import streamlit as st
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import html
import re

SCOPES = ['']


def gmail_authenticate():
    """Authenticate the user with Gmail API."""
    creds = None
    if 'token' in st.session_state:
        creds = Credentials.from_authorized_user_info(st.session_state['token'])
    else:
        try:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
            st.session_state['token'] = creds.to_json()
        except Exception as e:
            st.error(f"Authentication failed: {e}")
    return creds


def clean_text(text):
    """Remove invalid or non-displayable characters and decode HTML entities."""
    if not text:
        return ""
    text = html.unescape(text)
    text = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f-\x9f]', '', text)
    return text.strip()


def get_emails(service, max_results=10):
    """Fetch emails from Gmail inbox."""
    try:
        results = service.users().messages().list(userId='me', maxResults=max_results).execute()
        messages = results.get('messages', [])
        emails = []

        for msg in messages:
            txt = service.users().messages().get(userId='me', id=msg['id'], format='full').execute()
            headers = txt['payload'].get('headers', [])
            subject = sender = date = ""
            for d in headers:
                n = d.get('name', '').lower()
                if n == 'subject':
                    subject = d.get('value', '')
                elif n == 'from':
                    sender = d.get('value', '')
                elif n == 'date':
                    date = d.get('value', '')
            snippet = txt.get('snippet', '')
            emails.append({
                'id': msg['id'],
                'sender': clean_text(sender),
                'subject': clean_text(subject),
                'snippet': clean_text(snippet),
                'date': date
            })
        return emails

    except Exception as e:
        st.error(f"Error fetching emails: {e}")
        return []


def classify_email(email_text, sender="", subject=""):
    """Classify email into Urgent, Important, or Other with enhanced accuracy."""
    text = (email_text or '').lower()
    sender_lower = (sender or '').lower()
    subject_lower = (subject or '').lower()
    combined = text + " " + subject_lower

    # Trusted domains (emails from these are less likely to be spam)
    trusted_domains = [
        'google.com', 'microsoft.com', 'apple.com', 'amazon.com',
        'paypal.com', 'github.com', 'gitlab.com', 'linkedin.com',
        'facebook.com', 'twitter.com', 'instagram.com', 'netflix.com',
        'dropbox.com', 'slack.com', 'zoom.us', 'adobe.com',
        'salesforce.com', 'stripe.com', 'atlassian.com', 'notion.so'
    ]
    is_trusted = any(domain in sender_lower for domain in trusted_domains)

    urgent_security = [
        'security alert', 'security warning', 'suspicious activity', 'unusual activity',
        'unauthorized access', 'unusual sign-in', 'new login', 'login from',
        'verify your account', 'confirm your identity', 'account verification required',
        'password reset required', 'password changed', 'password reset',
        'suspicious login', 'login attempt', 'failed login', 'unusual location',
        'verification code', 'two-factor', '2fa', 'authentication code',
        'account locked', 'account disabled', 'account compromised',
        'data breach', 'security incident', 'fraud alert'
    ]

    urgent_financial = [
        'payment failed', 'payment declined', 'card declined', 'transaction failed',
        'payment overdue', 'subscription cancelled', 'subscription ending',
        'account suspended', 'service suspended', 'outstanding balance',
        'invoice overdue', 'payment bounced', 'insufficient funds',
        'billing issue', 'payment issue', 'auto-pay failed',
        'final notice', 'last warning', 'account will be closed'
    ]

    urgent_action = [
        'action required', 'immediate action', 'respond immediately',
        'urgent', 'asap', 'time sensitive', 'time-sensitive',
        'expires today', 'expiring soon', 'deadline today',
        'critical', 'emergency', 'important notice',
        'requires immediate attention', 'needs your attention'
    ]

    urgent_legal = [
        'legal notice', 'court notice', 'legal action',
        'lawsuit', 'violation', 'compliance required',
        'regulatory notice', 'tax notice', 'irs notice'
    ]

    important_work = [
        'meeting request', 'meeting invite', 'calendar invitation',
        'schedule', 'appointment', 'interview', 'call scheduled',
        'project update', 'status update', 'progress report',
        'review required', 'approval needed', 'please review',
        'feedback requested', 'input needed', 'action needed',
        'task assigned', 'assigned to you', 'deadline',
        'proposal', 'contract', 'agreement', 'document to sign',
        'performance review', 'annual review', '1:1 meeting'
    ]

    important_personal = [
        'order confirmation', 'order shipped', 'delivery update',
        'tracking information', 'package delivered', 'out for delivery',
        'booking confirmation', 'reservation confirmed', 'ticket',
        'appointment reminder', 'reservation reminder',
        'invoice', 'receipt', 'payment confirmation',
        'subscription renewal', 'membership renewal',
        'password reset', 'verification email', 'confirm email'
    ]

    important_updates = [
        'new message', 'direct message', 'you have been mentioned',
        'comment on', 'replied to', 'new comment', 'new reply',
        'shared with you', 'invited you', 'added you',
        'requested to', 'wants to', 'sent you',
        'notification from', 'update from', 'news from'
    ]

    spam_obvious = [
        'congratulations you won', 'you won', 'claim your prize', 'winner',
        'you\'ve been selected', 'selected winner', 'lucky winner',
        'click here now', 'click below', 'click this link',
        'act now', 'order now', 'buy now', 'shop now',
        'make money fast', 'make $$', 'earn money', 'work from home',
        'lose weight fast', 'weight loss miracle', 'diet pill',
        'viagra', 'cialis', 'pharmacy', 'prescription',
        'casino', 'lottery', 'gambling', 'poker',
        'risk free', '100% free', 'absolutely free',
        'no credit check', 'no strings attached',
        'billion dollars', 'million dollars', 'inheritance',
        'nigerian prince', 'transfer funds', 'bank transfer'
    ]

    spam_marketing = [
        'limited time offer', 'offer expires', 'today only',
        'don\'t miss out', 'last chance', 'hurry up',
        'exclusive deal', 'special offer', 'amazing deal',
        'lowest price', 'best price', 'price drop',
        'sale ends', 'flash sale', 'clearance sale',
        'up to % off', '% discount', 'save up to',
        'free trial', 'try for free', 'no obligation'
    ]

    promotional = [
        'newsletter', 'weekly digest', 'monthly update',
        'new arrivals', 'latest collection', 'new products',
        'recommendations for you', 'you might like',
        'based on your', 'personalized for you',
        'trending now', 'popular items', 'best sellers',
        'unsubscribe', 'manage preferences', 'email preferences'
    ]

    is_newsletter = any(word in combined for word in ['newsletter', 'digest', 'weekly roundup', 'unsubscribe'])
    is_marketing = any(word in combined for word in ['shop', 'sale', 'discount', 'deal', 'offer'])

    urgent_security_count = sum(1 for keyword in urgent_security if keyword in combined)
    urgent_financial_count = sum(1 for keyword in urgent_financial if keyword in combined)
    urgent_action_count = sum(1 for keyword in urgent_action if keyword in combined)
    urgent_legal_count = sum(1 for keyword in urgent_legal if keyword in combined)

    if urgent_security_count >= 1 or urgent_legal_count >= 1:
        return "Urgent"
    
    if urgent_financial_count >= 1 and is_trusted:
        return "Urgent"
    
    if urgent_action_count >= 1 and not is_marketing:
        return "Urgent"

    spam_obvious_count = sum(1 for keyword in spam_obvious if keyword in combined)
    spam_marketing_count = sum(1 for keyword in spam_marketing if keyword in combined)

    if spam_obvious_count >= 2:
        return "Other"
    
    if not is_trusted and spam_marketing_count >= 3:
        return "Other"

    important_work_count = sum(1 for keyword in important_work if keyword in combined)
    important_personal_count = sum(1 for keyword in important_personal if keyword in combined)
    important_updates_count = sum(1 for keyword in important_updates if keyword in combined)

    if important_work_count >= 1 and not is_newsletter:
        return "Important"
    
    if important_personal_count >= 1 and is_trusted:
        return "Important"
    
    if important_updates_count >= 1 and not is_marketing:
        return "Important"

    promotional_count = sum(1 for keyword in promotional if keyword in combined)
    if is_newsletter or promotional_count >= 2 or is_marketing:
        return "Other"

    if is_trusted and not is_marketing:
        return "Important"

    return "Other"


st.set_page_config(
    page_title="MailSort  - Email Dashboard",
    page_icon="📧",
    layout="wide",
    initial_sidebar_state="expanded"
)


if 'emails' not in st.session_state:
    st.session_state.emails = []
if 'current_view' not in st.session_state:
    st.session_state.current_view = 'Inbox'

st.markdown("""
<style>
    /* Light theme variables */
    :root {
        --bg-primary: #f8f9fa;
        --bg-secondary: #ffffff;
        --bg-tertiary: #f1f3f5;
        --text-primary: #212529;
        --text-secondary: #6c757d;
        --accent-blue: #3b82f6;
        --accent-red: #dc3545;
        --accent-orange: #fd7e14;
        --accent-green: #28a745;
        --border-color: #dee2e6;
        --urgent-bg: #fff5f5;
        --urgent-border: #dc3545;
        --important-bg: #fff8f0;
        --important-border: #fd7e14;
        --other-bg: #f0f7ff;
        --other-border: #3b82f6;
    }

    /* Global styles */
    .stApp {
        background: var(--bg-primary);
        color: var(--text-primary);
    }

    /* Hide Streamlit branding */
    #MainMenu, footer, header {visibility: hidden;}
    
    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background: var(--bg-secondary);
        border-right: 1px solid var(--border-color);
        padding-top: 1rem;
    }

    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] {
        color: var(--text-primary);
    }

    /* Logo section */
    .logo-section {
        padding: 1.5rem 1rem;
        margin-bottom: 1rem;
    }

    .logo-title {
        font-size: 1.5rem;
        font-weight: 700;
        color: var(--text-primary);
        margin: 0;
    }

    /* Main content area */
    .main-header {
        background: var(--bg-secondary);
        padding: 1.5rem 2rem;
        border-radius: 12px;
        margin-bottom: 1.5rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }

    .page-title {
        font-size: 2rem;
        font-weight: 700;
        color: var(--text-primary);
        margin: 0;
    }

    .search-box {
        background: var(--bg-tertiary);
        border: 1px solid var(--border-color);
        border-radius: 8px;
        padding: 0.75rem 1rem;
        display: flex;
        align-items: center;
        gap: 0.5rem;
        min-width: 300px;
    }

    .search-box input {
        background: transparent;
        border: none;
        color: var(--text-primary);
        outline: none;
        width: 100%;
    }

    /* Email table */
    .email-table {
        background: var(--bg-secondary);
        border-radius: 12px;
        overflow: hidden;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }

    .email-header {
        display: grid;
        grid-template-columns: 2fr 1.5fr 1fr;
        padding: 1rem 1.5rem;
        background: var(--bg-tertiary);
        border-bottom: 1px solid var(--border-color);
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        color: var(--text-secondary);
        letter-spacing: 0.5px;
    }

    .email-row {
        display: grid;
        grid-template-columns: 2fr 1.5fr 1fr;
        padding: 1.25rem 1.5rem;
        border-bottom: 1px solid var(--border-color);
        border-left: 4px solid;
        transition: all 0.2s;
        cursor: pointer;
        align-items: center;
    }

    .email-row:hover {
        transform: translateX(2px);
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }

    .email-row:last-child {
        border-bottom: none;
    }

    /* Colored email rows based on urgency */
    .email-row.urgent {
        background: var(--urgent-bg);
        border-left-color: var(--urgent-border);
    }

    .email-row.important {
        background: var(--important-bg);
        border-left-color: var(--important-border);
    }

    .email-row.other {
        background: var(--other-bg);
        border-left-color: var(--other-border);
    }

    .email-subject {
        font-weight: 500;
        color: var(--text-primary);
        font-size: 0.95rem;
    }

    .email-sender {
        color: var(--text-secondary);
        font-size: 0.9rem;
    }

    /* Badges */
    .badge {
        display: inline-block;
        padding: 0.35rem 0.75rem;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
    }

    .badge-urgent {
        background: var(--accent-red);
        color: white;
    }

    .badge-important {
        background: var(--accent-orange);
        color: white;
    }

    .badge-other {
        background: var(--accent-blue);
        color: white;
    }

    /* Buttons */
    .stButton button {
        background: transparent;
        border: 1px solid var(--border-color);
        color: var(--text-primary);
        padding: 0.6rem 1.2rem;
        border-radius: 8px;
        transition: all 0.2s;
    }

    .stButton button:hover {
        background: var(--bg-tertiary);
        border-color: var(--accent-blue);
    }

    /* Stats */
    .stat-box {
        background: var(--bg-secondary);
        padding: 1rem;
        border-radius: 8px;
        text-align: center;
        border: 1px solid var(--border-color);
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }

    .stat-number {
        font-size: 1.5rem;
        font-weight: 700;
        color: var(--text-primary);
    }

    .stat-label {
        font-size: 0.8rem;
        color: var(--text-secondary);
        margin-top: 0.25rem;
    }

    /* Empty state */
    .empty-state {
        background: var(--bg-secondary);
        padding: 3rem 2rem;
        border-radius: 12px;
        text-align: center;
        border: 1px solid var(--border-color);
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }

    .empty-state h3 {
        color: var(--text-primary);
        margin-bottom: 0.5rem;
    }

    .empty-state p {
        color: var(--text-secondary);
    }

    /* Slider customization */
    .stSlider {
        padding: 1rem 0;
    }

    /* Adjust spacing */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
</style>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.markdown("""
    <div class='logo-section'>
        <h1 class='logo-title'>MailSort📥 </h1>
    </div>
    """, unsafe_allow_html=True)

    # Navigation
    
    
    if st.button("Inbox", key="nav_inbox", use_container_width=True):
        st.session_state.current_view = "Inbox"
        st.rerun()
    
    if st.button(" Urgent", key="nav_urgent", use_container_width=True):
        st.session_state.current_view = "Urgent"
        st.rerun()
    
    if st.button(" Important", key="nav_important", use_container_width=True):
        st.session_state.current_view = "Important"
        st.rerun()
    
    if st.button("Other", key="nav_other", use_container_width=True):
        st.session_state.current_view = "Other"
        st.rerun()
    
    if st.button(" Sent", key="nav_sent", use_container_width=True):
        st.session_state.current_view = "Sent"
        st.rerun()

    st.markdown("<br><br>", unsafe_allow_html=True)
   
    st.markdown("### ⚙️ Settings")
    email_count = st.slider("Emails to fetch", 5, 50, 15, 5)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    if st.button("🔄 Connect & Fetch", key="fetch", use_container_width=True):
        creds = gmail_authenticate()
        if creds:
            service = build('gmail', 'v1', credentials=creds)
            with st.spinner("Fetching emails..."):
                st.session_state.emails = get_emails(service, email_count)
            if st.session_state.emails:
                st.success(f"✓ Fetched {len(st.session_state.emails)} emails")
                st.rerun()

    # Statistics
    if st.session_state.emails:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("### 📊 Statistics")
        
        classified = []
        for email in st.session_state.emails:
            category = classify_email(
                email['snippet'], 
                email['sender'],
                email['subject']
            )
            classified.append({**email, 'category': category})

        urgent_count = sum(1 for e in classified if e['category'] == 'Urgent')
        important_count = sum(1 for e in classified if e['category'] == 'Important')
        other_count = sum(1 for e in classified if e['category'] == 'Other')

        st.markdown(f"""
        <div class='stat-box'>
            <div class='stat-number'>{len(classified)}</div>
            <div class='stat-label'>Total</div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"""
            <div class='stat-box'>
                <div class='stat-number' style='color: #dc3545;'>{urgent_count}</div>
                <div class='stat-label'>Urgent</div>
            </div>
            """, unsafe_allow_html=True)
        with col2:
            st.markdown(f"""
            <div class='stat-box'>
                <div class='stat-number' style='color: #fd7e14;'>{important_count}</div>
                <div class='stat-label'>Important</div>
            </div>
            """, unsafe_allow_html=True)

st.markdown(f"""
<div class='main-header'>
    <h1 class='page-title'>{st.session_state.current_view}</h1>
    <div class='search-box'>
        <span>🔍</span>
        <input type='text' placeholder='Search mail' readonly />
    </div>
</div>
""", unsafe_allow_html=True)

if st.session_state.emails:

    classified = []
    for email in st.session_state.emails:
        category = classify_email(
            email['snippet'], 
            email['sender'],
            email['subject']
        )
        classified.append({**email, 'category': category})

    # Filter based on current view
    if st.session_state.current_view == 'Inbox':
        filtered = classified
    elif st.session_state.current_view in ['Urgent', 'Important', 'Other']:
        filtered = [e for e in classified if e['category'] == st.session_state.current_view]
    else:
        filtered = []

    # Email table
    st.markdown("""
    <div class='email-table'>
        <div class='email-header'>
            <div>SUBJECT</div>
            <div>SENDER</div>
            <div>URGENCY</div>
        </div>
    """, unsafe_allow_html=True)

    if len(filtered) == 0:
        st.markdown("""
        <div style='padding: 3rem; text-align: center; color: var(--text-secondary);'>
            No emails in this category
        </div>
        """, unsafe_allow_html=True)
    else:
        for email in filtered:
            category = email['category']
            badge_class = f"badge-{category.lower()}"
            row_class = category.lower()
           
            sender_display = email['sender'].split('<')[0].strip() if '<' in email['sender'] else email['sender']
            
            st.markdown(f"""
            <div class='email-row {row_class}'>
                <div class='email-subject'>{html.escape(email['subject'][:80])}</div>
                <div class='email-sender'>{html.escape(sender_display[:50])}</div>
                <div><span class='badge {badge_class}'>{category}</span></div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

else:
    st.markdown("""
    <div class='empty-state'>
        <h3>No Emails Loaded</h3>
        <p>Connect your Gmail account to start organizing your inbox</p>
        <br>
        <p style='font-size: 0.9rem;'>🔒 Secure OAuth2 • 🤖 AI Sorting • ⚡ Fast Preview</p>
    </div>
    """, unsafe_allow_html=True)