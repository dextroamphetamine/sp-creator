from datetime import timedelta

class Config:
    # Secret Key
    SECRET_KEY = 'your_secret_key_here'  # Make sure to keep this secret and unique

    SESSION_TYPE = 'filesystem'
    # Session Configuration
    SESSION_COOKIE_NAME = 'replit_session_cookie'
    SESSION_COOKIE_SAMESITE = 'Lax'  # Lax is a safer default than None
    SESSION_COOKIE_DOMAIN = None  # Let Flask set this automatically
    SESSION_COOKIE_PATH = '/'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = True  # Since you're using HTTPS
    SESSION_PERMANENT = True
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)  # Set session to 7 days