class ApiKeyNotDefinedError(Exception):
    def __init__(self, env_key: str):
        self.env_key = env_key
        super().__init__(f"API Key has not been configured: {env_key}")
