# """
# Authentication helper to check and manage user OAuth scopes.
# """

# from typing import List, Optional
# from google.oauth2.credentials import Credentials
# from loguru import logger

# REQUIRED_SCOPES = [
#     "https://www.googleapis.com/auth/tasks",
#     "https://www.googleapis.com/auth/calendar"
# ]

# def check_user_has_required_scopes(creds: Credentials) -> bool:
#     """
#     Check if the user has all required scopes for task and calendar integration.
#     """
#     if not hasattr(creds, 'scopes') or not creds.scopes:
#         logger.warning("No scopes found in credentials")
#         return False
    
#     current_scopes = set(creds.scopes)
#     required_scopes = set(REQUIRED_SCOPES)
    
#     # Check for scope conflicts (read-only vs full access)
#     scope_conflicts = []
#     if "https://www.googleapis.com/auth/tasks.readonly" in current_scopes and "https://www.googleapis.com/auth/tasks" in current_scopes:
#         scope_conflicts.append("tasks: both readonly and full access")
#     if "https://www.googleapis.com/auth/calendar.readonly" in current_scopes and "https://www.googleapis.com/auth/calendar" in current_scopes:
#         scope_conflicts.append("calendar: both readonly and full access")
    
#     if scope_conflicts:
#         logger.warning(f"Scope conflicts detected: {scope_conflicts}")
    
#     missing_scopes = required_scopes - current_scopes
    
#     if missing_scopes:
#         logger.warning(f"Missing required scopes: {missing_scopes}")
#         return False
    
#     logger.info("User has all required scopes")
#     return True

# def get_missing_scopes(creds: Credentials) -> List[str]:
#     """
#     Get list of missing scopes for the user.
#     """
#     if not hasattr(creds, 'scopes') or not creds.scopes:
#         return REQUIRED_SCOPES
    
#     current_scopes = set(creds.scopes)
#     required_scopes = set(REQUIRED_SCOPES)
    
#     # Remove any read-only versions of scopes we need full access to
#     current_scopes.discard("https://www.googleapis.com/auth/tasks.readonly")
#     current_scopes.discard("https://www.googleapis.com/auth/calendar.readonly")
    
#     return list(required_scopes - current_scopes)

# def force_reauthentication_url() -> str:
#     """
#     Generate a URL that forces re-authentication with all required scopes.
#     """
#     from services.google_oauth import build_flow
    
#     # Build flow with prompt=consent to force re-authentication
#     flow = build_flow()
#     flow.prompt = "consent"  # This forces the consent screen to appear
    
#     auth_url, state = flow.authorization_url(
#         access_type="offline",
#         include_granted_scopes="true",
#         prompt="consent",  # Force consent screen
#     )
    
#     return auth_url 