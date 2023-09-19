from .github_template import GitHubTemplate

github_template = GitHubTemplate()


class TestGitHubTemplate:
    # def test_get_template_repos(self):
    #     templates = github_template.get_template_repos()
    #
    #     print(f'found {templates.totalCount} template repos')
    #     i = 0
    #     for template in templates:
    #         i += 1
    #         print(f'#{i}: {template.name} {template.is_template}')

    # def test_get_template_repos_by_label(self):
    #     # When
    #     repo_embeddings = github_template.get_template_repos()

    # def test_generate_embeddings_for_repos(self):
    #     # When
    #     repo_embeddings = github_template.generate_embeddings_for_repos()

    def test_recommend_template_repositories(self):
        repo_embeddings = github_template.generate_embeddings_for_repos()

        # When
        recommended = github_template.recommend_template_repositories(
            'A simple chat app with real time communication',
            repo_embeddings)

        # Then
        assert recommended[0]['repo'] == 'machaao/machaao-wit-template'

    def test_recommend_template_repositories_with_technologies(self):
        repo_embeddings = github_template.generate_embeddings_for_repos()

        # When
        recommended = github_template.recommend_template_repositories(
            'A simple chat app with real time communication. Technologies: TypeScript, React',
            repo_embeddings)

        # Then
        assert recommended[0]['repo'] == 'lebrancconvas/React-Typescript-Template'

    def test_recommend_template_repositories_intellij(self):
        repo_embeddings = github_template.generate_embeddings_for_repos()

        # When
        recommended = github_template.recommend_template_repositories(
            'An IntelliJ plugin to use GPT Pilot to build software projects. Technologies: Kotlin, Gradle, IntelliJ SDK',
            repo_embeddings)

        # Then
        assert recommended[0]['repo'] == []
