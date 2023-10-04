class TokenLimitError(Exception):
    def __init__(self, tokens_in_messages, max_tokens):
        self.tokens_in_messages = tokens_in_messages
        self.max_tokens = max_tokens
        super().__init__(f"Token limit error happened with {tokens_in_messages}/{max_tokens} tokens in messages!")
