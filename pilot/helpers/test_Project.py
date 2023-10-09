import pytest
from unittest.mock import patch
from helpers.Project import Project
from database.models.files import File


def create_project():
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
    return project


class TestProject:
    def test_save_file_permutations(self):
        project = create_project()
        project.root_path = '/Users/zvonimirsabljic/Development/copilot/pilot'

        values = [
            "",
            "server.js",
            "~/",
            "~/server.js",
            "/",
            "/server.js",
            "/Users/zvonimirsabljic/Development/copilot/pilot",
            "/Users/zvonimirsabljic/Development/copilot/pilot/",
            "/Users/zvonimirsabljic/Development/copilot/pilot/server.js"
        ]

        for file_name in values:
            if file_name.endswith('server.js'):
                for file_path in values:
                    out_file_path, absolute_path = project.get_full_file_path(file_path, file_name)
                    # print(f"file_path: {file_path} -> {out_file_path}, \tabsolute_path: {absolute_path}")
                    assert out_file_path == '', f'file_path: {file_path}, file_name: {file_name}'
                    # if absolute_path != '/Users/zvonimirsabljic/Development/copilot/pilot/server.js':
                    #     print(f'file_path: {file_path}, file_name: {file_name}')
                    assert absolute_path == '/Users/zvonimirsabljic/Development/copilot/pilot/server.js',\
                        f'file_path: {file_path}, file_name: {file_name}'

    def test_save_file_permutations_deeper(self):
        project = create_project()
        project.root_path = '/Users/zvonimirsabljic/Development/copilot/pilot'

        values = [
            "",
            "/",
            "~/",
            "folder1/folder2/server.js",
            "/folder1/folder2/server.js",
            "~/folder1/folder2/server.js",
            "/Users/zvonimirsabljic/Development/copilot/pilot/folder1/folder2/server.js",

            "folder1/",
            "/folder1/",
            "~/folder1/",
            "/Users/zvonimirsabljic/Development/copilot/pilot/folder1/",

            "folder1",
            "/folder1",
            "~/folder1",
            "/Users/zvonimirsabljic/Development/copilot/pilot/folder1",

            "folder1/folder2/",
            "/folder1/folder2/",
            "~/folder1/folder2/",
            "/Users/zvonimirsabljic/Development/copilot/pilot/folder1/folder2/",

            "folder1/folder2",
            "/folder1/folder2",
            "~/folder1/folder2",
            "/Users/zvonimirsabljic/Development/copilot/pilot/folder1/folder2",

            "server.js",
            "/server.js",
            "~/server.js",

            "folder2/server.js",
            "/folder2/server.js",
            "~/folder2/server.js",
            "/Users/zvonimirsabljic/Development/copilot/pilot/folder2/server.js",
        ]
        # values = ['', 'folder1/folder2/server.js']

        for file_name in values:
            if file_name.endswith('server.js'):
                for file_path in values:
                    expected_path = ''
                    if 'folder1' in file_path:
                        if 'folder1/folder2' in file_path:
                            expected_path = 'folder1/folder2'
                        else:
                            expected_path = 'folder1'
                    elif 'folder2' in file_path:
                        expected_path = 'folder2'

                    expected_absolute_path = project.root_path + \
                                             ('' if expected_path == '' else '/' + expected_path) + '/server.js'

                    out_file_path, absolute_path = project.get_full_file_path(file_path, file_name)
                    # print(f"file_path: {file_path} -> {out_file_path}, \tabsolute_path: {absolute_path}")
                    assert out_file_path == expected_path, f'file_path: {file_path}, file_name: {file_name}'
                    # if absolute_path != expected_absolute_path:
                    #     print(f'file_path: {file_path}, file_name: {file_name}')
                    assert absolute_path == expected_absolute_path, f'file_path: {file_path}, file_name: {file_name}'

    def test_save_file_permutations_windows(self):
        project = create_project()
        project.root_path = 'C:\\Users\\zvonimirsabljic\\Development\\copilot\\pilot'

        values = [
            "",
            "server.js",
            "~\\",
            "~\\server.js",
            "C:\\",
            "C:\\server.js",
            "C:\\Users\\zvonimirsabljic\\Development\\copilot\\pilot",
            "C:\\Users\\zvonimirsabljic\\Development\\copilot\\pilot\\",
            "C:\\Users\\zvonimirsabljic\\Development\\copilot\\pilot\\server.js"
        ]
        values = ['C:\\Users\\zvonimirsabljic\\Development\\copilot\\pilot', 'server.js']

        for file_name in values:
            if file_name.endswith('server.js'):
                for file_path in values:
                    out_file_path, absolute_path = project.get_full_file_path(file_path, file_name)
                    # print(f"file_path: {file_path} -> {out_file_path}, \tabsolute_path: {absolute_path}")
                    assert out_file_path == '', f'file_path: {file_path}, file_name: {file_name}'
                    # if absolute_path != '/Users/zvonimirsabljic/Development/copilot/pilot/server.js':
                    #     print(f'file_path: {file_path}, file_name: {file_name}')
                    assert absolute_path == project.root_path + '/server.js',\
                        f'file_path: {file_path}, file_name: {file_name}'

    def test_save_file_permutations_windows_deeper(self):
        project = create_project()
        project.root_path = 'C:\\Users\\zvonimirsabljic\\Development\\copilot\\pilot'

        values = [
            "",
            "C:\\",
            "~\\",
            "fol der1\\fold er2\\server.js",
            "C:\\folder1\\folder2\\server.js",
            "~\\folder1\\folder2\\server.js",
            "C:\\Users\\zvonimirsabljic\\Development\\copilot\\pilot\\folder1\\folder2\\server.js",

            "folder1\\",
            "C:\\folder1\\",
            "~\\folder1\\",
            "\\Users\\zvonimirsabljic\\Development\\copilot\\pilot\\folder1\\",

            "folder1",
            "C:\\folder1",
            "~\\folder1",
            "C:\\Users\\zvonimirsabljic\\Development\\copilot\\pilot\\folder1",

            "folder1\\folder2\\",
            "C:\\folder1\\folder2\\",
            "~\\folder1\\folder2\\",
            "C:\\Users\\zvonimirsabljic\\Development\\copilot\\pilot\\folder1\\folder2\\",

            "folder1\\folder2",
            "C:\\folder1\\folder2",
            "~\\folder1\\folder2",
            "C:\\Users\\zvonimirsabljic\\Development\\copilot\\pilot\\folder1\\folder2",

            "server.js",
            "C:\\server.js",
            "~\\server.js",

            "folder2\\server.js",
            "C:\\folder2\\server.js",
            "~\\folder2\\server.js",
            "C:\\Users\\zvonimirsabljic\\Development\\copilot\\pilot\\folder2\\server.js",
        ]
        values = ['C:\\Users\\zvonimirsabljic\\Development\\copilot\\pilot', 'server.js']

        for file_name in values:
            if file_name.endswith('server.js'):
                for file_path in values:
                    expected_path = ''
                    if 'folder1' in file_path:
                        if 'folder1/folder2' in file_path:
                            expected_path = 'folder1/folder2'
                        else:
                            expected_path = 'folder1'
                    elif 'folder2' in file_path:
                        expected_path = 'folder2'

                    expected_absolute_path = project.root_path + \
                                             ('' if expected_path == '' else '/' + expected_path) + '/server.js'

                    out_file_path, absolute_path = project.get_full_file_path(file_path, file_name)
                    # print(f"file_path: {file_path} -> {out_file_path}, \tabsolute_path: {absolute_path}")
                    assert out_file_path == expected_path, f'file_path: {file_path}, file_name: {file_name}'
                    # if absolute_path != expected_absolute_path:
                    #     print(f'file_path: {file_path}, file_name: {file_name}')
                    assert absolute_path == expected_absolute_path, f'file_path: {file_path}, file_name: {file_name}'

    @pytest.mark.parametrize('test_data', [
        {'name': 'package.json', 'path': 'package.json', 'saved_to': '/temp/gpt-pilot-test/package.json'},
        {'name': 'package.json', 'path': '', 'saved_to': '/temp/gpt-pilot-test/package.json'},
        {'name': 'package.json', 'path': '/', 'saved_to': '/temp/gpt-pilot-test/package.json'},  # observed scenario
        {'name': 'Dockerfile', 'path': None, 'saved_to': '/temp/gpt-pilot-test/Dockerfile'},
        {'name': None, 'path': 'public/index.html', 'saved_to': '/temp/gpt-pilot-test/public/index.html'},
        {'name': '', 'path': 'public/index.html', 'saved_to': '/temp/gpt-pilot-test/public/index.html'},

        # TODO: Treatment of paths outside of the project workspace - https://github.com/Pythagora-io/gpt-pilot/issues/129
        # {'name': '/etc/hosts', 'path': None, 'saved_to': '/etc/hosts'},
        # {'name': '.gitconfig', 'path': '~', 'saved_to': '~/.gitconfig'},
        # {'name': '.gitconfig', 'path': '~/.gitconfig', 'saved_to': '~/.gitconfig'},
        # {'name': 'gpt-pilot.log', 'path': '/temp/gpt-pilot.log', 'saved_to': '/temp/gpt-pilot.log'},
    # ], ids=[
    #     'name == path', 'empty path', 'slash path',
    #     # 'None path',
    #     'None name', 'empty name',
        # 'None path absolute file', 'home path', 'home path same name', 'absolute path with name'
    ])
    @patch('helpers.Project.update_file')
    @patch('helpers.Project.File')
    def test_save_file(self, mock_file_insert, mock_update_file, test_data):
        # Given
        data = {'content': 'Hello World!'}
        if test_data['name'] is not None:
            data['name'] = test_data['name']
        if test_data['path'] is not None:
            data['path'] = test_data['path']

        project = create_project()

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
    def test_get_full_path(self, file_path, file_name, expected):
        # Given
        project = create_project()

        # When
        relative_path, absolute_path = project.get_full_file_path(file_path, file_name)

        # Then
        assert absolute_path == expected

    @pytest.mark.skip(reason="Handling of absolute paths will be revisited in #29")
    @pytest.mark.parametrize('file_path, file_name, expected', [
        ('/file.txt', 'file.txt', '/file.txt'),
        ('/path/to/file.txt', 'file.txt', '/path/to/file.txt'),
        # Only passes on Windows? ('C:\\path\\to\\file.txt', 'file.txt', 'C:\\path\\to/file.txt'),
        ('~/path/to/file.txt', 'file.txt', '~/path/to/file.txt'),
    ])
    def test_get_full_path_absolute(self, file_path, file_name, expected):
        # Given
        project = create_project()

        # When
        relative_path, absolute_path = project.get_full_file_path(file_path, file_name)

        # Then
        assert absolute_path == expected

    # # This is known to fail and should be avoided
    # def test_get_full_file_path_error(self):
    #     # Given
    #     project = create_project()
    #     file_path = 'path/to/file/'
    #     file_name = ''
    #
    #     # When
    #     relative_path, full_path = project.get_full_file_path(file_path, file_name)
    #
    #     # Then
    #     assert full_path == '/temp/gpt-pilot-test/path/to/file/'
