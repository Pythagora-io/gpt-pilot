import os
from .files import get_files_content


def test_get_files_content():
    # Given
    directory = os.path.dirname(__file__)

    # When
    files = get_files_content(directory, ['.pytest_cache', '__pycache__',
                                          'agents', 'detectors', 'project_scaffold', 'story_manager'])

    # Then
    assert len(files) > 0
    assert files[0]['path'] == ''
    assert files[0]['full_path'].startswith(directory)
    # TODO: could the leading / cause files being written back to the root directory?
    assert any(file['path'] == '/exceptions' for file in files)
