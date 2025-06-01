from datetime import datetime
from utils.errors import ValidationError
import re

def validate_date(date_str):
    print("Validating date ", date_str)
    try:
        # Remove trailing 'Z' for UTC if present, as fromisoformat doesn't accept it
        date_str = re.sub(r"Z$", "", date_str)
        # Attempt to parse the date and return a datetime object
        print("Date validated")
        return datetime.fromisoformat(date_str)# ISO format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)
    except ValueError:
        print(f"Invalid date format for '{date_str}'. Expected ISO format: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS.")
        raise ValidationError(f"Invalid date format for '{date_str}'. Expected ISO format: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS.")
    