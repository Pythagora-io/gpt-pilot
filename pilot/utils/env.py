from os import getenv

class ApiKeyNotDefinedError(Exception):
    def __init__(self, env_key: str):
        self.env_key = env_key
        super().__init__(f"API Key has not been configured: {env_key}")

def get_api_key_or_throw(env_key: str):
    api_key = getenv(env_key)
    if api_key is None:
        raise ApiKeyNotDefinedError(env_key)
    return api_key