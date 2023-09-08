import os
from .run_detectors import run_detectors
from ..Project import Project


def test_javascript_project_detection():
    # Given
    project = create_project('javascript')

    # When
    config = run_detectors(project)

    # Then
    assert config.language == 'JavaScript'


def test_typescript_project_detection():
    # Given
    project = create_project('typescript')

    # When
    config = run_detectors(project)

    # Then
    assert config.language == 'TypeScript'


def test_maven_project_detection():
    # Given
    project = create_project('maven')

    # When
    config = run_detectors(project)

    # Then
    assert config.language == 'Java'


def test_python_project_detection():
    # Given
    project = create_project('python')

    # When
    config = run_detectors(project)

    # Then
    assert config.language == 'Python'


def test_project_detection_skipped_without_workspace():
    # Given
    project = Project(args={
        'name': None
    })

    # When
    config = run_detectors(project)

    # Then
    assert config.language is None


def test_project_detection_skipped_none_workspace():
    # Given
    project = Project(args={
        'name': None,
        'workspace': None,
    })

    # When
    config = run_detectors(project)

    # Then
    assert config.language is None


def create_project(name) -> Project:
    return Project(args={
        'name': None,
        'workspace': os.path.join(os.path.dirname(__file__), 'test', name)
    })
