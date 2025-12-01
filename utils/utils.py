def get_unique_id(len: int = 8):
    import secrets

    unique_id = secrets.token_hex(8)
    return unique_id
