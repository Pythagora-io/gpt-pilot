generators = []


def project_generator(name=None, language=None, topics=None):
    def decorator(cls):
        generators.append(cls)
        cls.is_project_generator = True
        cls.name = name
        cls.language = language
        cls.topics = topics
        return cls
    return decorator
