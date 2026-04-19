def validate_response(response, required_keys):
    for key in required_keys:
        if key not in response:
            raise ValueError(f"Missing key: {key}")
    return True
