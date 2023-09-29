class TooDeepRecursionError(Exception):
    def __init__(self, message='Recursion is too deep!'):
        self.message = message
        super().__init__(message)
