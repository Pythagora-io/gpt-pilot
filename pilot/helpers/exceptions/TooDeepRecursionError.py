class TooDeepRecursionError(Exception):
    def __init__(self, context=None, message='Recursion is too deep!'):
        if context:
            message = f"{message} (Context: {context})"
        super().__init__(message)