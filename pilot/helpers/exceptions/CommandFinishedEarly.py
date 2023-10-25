class CommandFinishedEarly(Exception):
    def __init__(self, message='Command finished before timeout. Handling early completion...'):
        self.message = message
        super().__init__(message)