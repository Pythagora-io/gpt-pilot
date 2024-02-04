import json

from const.llm import MAX_GPT_MODEL_TOKENS


class ApiKeyNotDefinedError(Exception):
    def __init__(self, env_key: str):
        self.env_key = env_key
        super().__init__(f"API Key has not been configured: {env_key}")


class CommandFinishedEarly(Exception):
    def __init__(self, message='Command finished before timeout. Handling early completion...'):
        self.message = message
        super().__init__(message)


class TokenLimitError(Exception):
    def __init__(self, tokens_in_messages, max_tokens=MAX_GPT_MODEL_TOKENS):
        self.tokens_in_messages = tokens_in_messages
        self.max_tokens = max_tokens
        super().__init__(f"Token limit error happened with {tokens_in_messages}/{max_tokens} tokens in messages!")


class TooDeepRecursionError(Exception):
    def __init__(self, message='Recursion is too deep!'):
        self.message = message
        super().__init__(message)


class ApiError(Exception):
    def __init__(self, message, response=None):
        self.message = message
        self.response = response
        self.response_json = None
        if response and hasattr(response, "text"):
            try:
                self.response_json = json.loads(response.text)
            except Exception:  # noqa
                pass

        super().__init__(message)


class GracefulExit(Exception):
    def __init__(self, message='Graceful exit'):
        self.message = message
        super().__init__(message)
