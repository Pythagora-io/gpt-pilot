class MockQuestionary:
    def __init__(self, answers=None):
        if answers is None:
            answers = []
        self.answers = iter(answers)
        self.state = 'project_description'

    def text(self, question: str, style=None):
        print('AI: ' + question)
        if question.startswith('User Story'):
            self.state = 'user_stories'
        elif question.endswith('write "DONE"'):
            self.state = 'DONE'
        return self

    def unsafe_ask(self):
        if self.state == 'user_stories':
            answer = ''
        elif self.state == 'DONE':
            answer = 'DONE'
        else:  # if self.state == 'project_description':
            answer = next(self.answers, '')

        print('User:', answer)
        return answer
