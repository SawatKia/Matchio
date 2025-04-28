from datetime import datetime
from zoneinfo import ZoneInfo

def get_bangkok_time() -> datetime:
    """
    Get current time in Bangkok timezone.
    
    Returns:
        Current datetime in Bangkok timezone
    """
    return datetime.now(ZoneInfo('Asia/Bangkok'))