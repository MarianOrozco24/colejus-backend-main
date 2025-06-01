from utils.errors import ValidationError

def validate_fields(json_dict, required_fields):
    print("Validating fields")
    missing_fields = [field for field in required_fields if field not in json_dict]
    if missing_fields:
        print(f"Missing fields: {', '.join(missing_fields)}")
        raise ValidationError(f"Missing required fields: {', '.join(missing_fields)}")
    print("Fields validated")