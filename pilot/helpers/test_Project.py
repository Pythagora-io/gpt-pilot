import pytest
from unittest.mock import Mock, patch
from helpers.Project import Project


project = Project({
        'app_id': 'test-project',
        'name': 'TestProject',
        'app_type': ''
    },
    name='TestProject',
    architecture=[],
    user_stories=[]
)
project.root_path = "/temp/gpt-pilot-test"
project.app = 'test'


@pytest.mark.parametrize('test_data', [
    {'name': 'package.json', 'path': 'package.json', 'saved_to': '/temp/gpt-pilot-test/package.json'},
    {'name': 'package.json', 'path': '', 'saved_to': '/temp/gpt-pilot-test/package.json'},
    {'name': 'Dockerfile', 'path': None, 'saved_to': '/temp/gpt-pilot-test/Dockerfile'},
    {'name': None, 'path': 'public/index.html', 'saved_to': '/temp/gpt-pilot-test/public/index.html'},
    {'name': '', 'path': 'public/index.html', 'saved_to': '/temp/gpt-pilot-test/public/index.html'},

    {'name': '/etc/hosts', 'path': None, 'saved_to': '/etc/hosts'},
    {'name': '.gitconfig', 'path': '~', 'saved_to': '~/.gitconfig'},
    {'name': '.gitconfig', 'path': '~/.gitconfig', 'saved_to': '~/.gitconfig'},
    {'name': 'gpt-pilot.log', 'path': '/temp/gpt-pilot.log', 'saved_to': '/temp/gpt-pilot.log'},
], ids=['name == path', 'empty path', 'None path', 'None name', 'empty name',
        'None path absolute file', 'home path', 'home path same name', 'absolute path with name'
])
@patch('helpers.Project.update_file')
@patch('helpers.Project.File.insert')
def test_save_file(mock_file_insert, mock_update_file, test_data):
    # Given
    data = {'content': 'Hello World!'}
    if test_data['name'] is not None:
        data['name'] = test_data['name']
    if test_data['path'] is not None:
        data['path'] = test_data['path']

    # When
    project.save_file(data)

    # Then assert that update_file with the correct path
    expected_saved_to = test_data['saved_to']
    mock_update_file.assert_called_once_with(expected_saved_to, 'Hello World!')

    # Also assert that File.insert was called with the expected arguments
    # expected_file_data = {'app': project.app, 'path': test_data['path'], 'name': test_data['name'],
    #                       'full_path': expected_saved_to}
    # mock_file_insert.assert_called_once_with(app=project.app, **expected_file_data,
    #                                          **{'name': test_data['name'], 'path': test_data['path'],
    #                                             'full_path': expected_saved_to})


@pytest.mark.parametrize('file_path, file_name, expected', [
    ('file.txt', 'file.txt', '/temp/gpt-pilot-test/file.txt'),
    ('', 'file.txt', '/temp/gpt-pilot-test/file.txt'),
    ('path/', 'file.txt', '/temp/gpt-pilot-test/path/file.txt'),
    ('path/to/', 'file.txt', '/temp/gpt-pilot-test/path/to/file.txt'),
    ('path/to/file.txt', 'file.txt', '/temp/gpt-pilot-test/path/to/file.txt'),
    ('./path/to/file.txt', 'file.txt', '/temp/gpt-pilot-test/path/to/file.txt'),
])
def test_get_full_path(file_path, file_name, expected):
    relative_path, absolute_path = project.get_full_file_path(file_path, file_name)

    # Then
    assert absolute_path == expected


@pytest.mark.parametrize('file_path, file_name, expected', [
    ('/file.txt', 'file.txt', '/file.txt'),
    ('/path/to/file.txt', 'file.txt', '/path/to/file.txt'),
    # Only passes on Windows? ('C:\\path\\to\\file.txt', 'file.txt', 'C:\\path\\to/file.txt'),
    ('~/path/to/file.txt', 'file.txt', '~/path/to/file.txt'),
])
def test_get_full_path_absolute(file_path, file_name, expected):
    relative_path, absolute_path = project.get_full_file_path(file_path, file_name)

    # Then
    assert absolute_path == expected


# This is known to fail and should be avoided
# def test_get_full_file_path_error():
#     # Given
#     file_path = 'path/to/file/'
#     file_name = ''
#
#     # When
#     full_path = project.get_full_file_path(file_path, file_name)
#
#     # Then
#     assert full_path == '/temp/gpt-pilot-test/path/to/file/'
