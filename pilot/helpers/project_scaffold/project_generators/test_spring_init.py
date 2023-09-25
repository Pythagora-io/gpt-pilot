from .spring_init import SpringInit


class TestSpringInit:
    def test_get_dependencies(self):
        spring_init = SpringInit()

        # When
        dependencies = spring_init.get_dependencies()

        # Then
        assert len(dependencies) > 0
