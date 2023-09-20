import pytest
from .github_templates import GitHubTemplates

github_templates = GitHubTemplates()


class TestGitHubTemplate:
    def test_get_template_repos(self):
        templates = github_templates.get_template_repos()

        # print(f'found {templates.totalCount} template repos')
        assert templates.totalCount > 0
        # assert templates.totalCount < 1000
        ignored_templates = [t for t in templates if t.full_name == 'cirosantilli/china-dictatorship']
        assert not ignored_templates, 'ignored templates found'
    #
    #     # i = 0
    #     # for template in templates:
    #     #     i += 1
    #     #     print(f'#{i}: {template.full_name}')

    @pytest.mark.slow
    @pytest.mark.daily
    def test_generate_embeddings_for_public_repos(self):
        # When
        repo_embeddings = github_templates.generate_embeddings_for_public_repos()

        # Then
        assert len(repo_embeddings) > 0

    def test_recommend_template_repositories(self):
        repo_embeddings = github_templates.get_embeddings()

        # When
        recommended = github_templates.recommend_template_repositories(
            'A simple chat app with real time communication',
            repo_embeddings)

        # Then
        self.print_recommendations(recommended)
        assert recommended[0]['repo'] == 'vercel-labs/ai-chatbot'

    # def test_recommend_template_repositories_with_technologies(self):
    #     repo_embeddings = github_templates.generate_embeddings_for_repos()
    #
    #     # When
    #     recommended = github_template.recommend_template_repositories(
    #         'A simple chat app with real time communication.',
    #         technologies=['TypeScript', 'Vue'],
    #         repo_embeddings=repo_embeddings)
    #
    #     # Then
    #     self.print_recommendations(recommended)
    #     assert recommended[0]['repo'] == 'should be something Vue related'

    def test_recommend_template_repositories_python(self):
        repo_embeddings = github_templates.get_embeddings()

        # When
        recommended = github_templates.recommend_template_repositories(
            'A Python backend using FastAPI.',
            repo_embeddings)

        # Then
        self.print_recommendations(recommended)
        assert recommended[0]['repo'] == 'teamhide/fastapi-boilerplate'

    def test_recommend_template_repositories_intellij(self):
        repo_embeddings = github_templates.get_embeddings()

        # When
        recommended = github_templates.recommend_template_repositories(
            'An IntelliJ plugin to use GPT Pilot to build software projects.',
            # Technologies:
            # 'Kotlin, Python, IntelliJ, JetBrains Settings UI, GitHub Actions',
            repo_embeddings)

        # Then
        self.print_recommendations(recommended)
        assert recommended[0]['repo'] == 'JetBrains/intellij-platform-plugin-template'

    def print_recommendations(self, recommended):
        for repo in recommended:
            print(f"  {repo['repo']} ({repo['stars']}) - {repo['description']}")
