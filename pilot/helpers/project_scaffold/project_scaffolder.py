from .project_generators.project_generators import ProjectGenerators
from .project_templates.github_templates import GitHubTemplates
from helpers.AgentConvo import AgentConvo
from const.function_calls import CREATE_PROJECT


class ProjectScaffolder:
    def __init__(self):
        self.github_templates = GitHubTemplates()
        self.generators = ProjectGenerators()

    def select_project_generator(self, project, convo: AgentConvo):
        description = project.description
        github_templates = self.github_templates.recommend_template_repositories(description)

        generators = self.generators.recommend(description)

        selected = convo.send_message('development/select_project_generator.prompt', {
            'description': description,
            'github_templates': github_templates,
            'generators': generators
        }, CREATE_PROJECT)

        return selected

