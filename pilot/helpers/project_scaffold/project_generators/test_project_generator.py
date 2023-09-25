import pytest

from .project_generators import ProjectGenerators

generators = ProjectGenerators()


@pytest.mark.uses_tokens
class TestProjectGenerators:
    def test_get_embeddings(self):
        # When
        embeddings = generators.get_embeddings()

        # Then
        assert len(embeddings) == 7

    def test_recommend_web(self):
        # When
        recommended = generators.recommend('A web-based email app.')

        # Then
        assert len(recommended) > 0
        assert recommended[0]['name'] == 'create-react-app'


    def test_recommend_next(self):
        # When
        recommended = generators.recommend('A web-based email app using Next.JS.')

        # Then
        assert len(recommended) > 0
        assert recommended[0]['name'] == 'create-next-app'

    def test_recommend_kotlin(self):
        # When
        recommended = generators.recommend('A Kotlin API.')

        # Then
        assert len(recommended) > 0
        assert recommended[0]['name'] == 'Gradle Init'

    def test_recommend_mobile(self):
        # When
        recommended = generators.recommend('A mobile app')

        # Then
        assert len(recommended) > 0
        assert recommended[0]['name'] == 'flutter'