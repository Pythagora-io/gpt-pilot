import os


APP_TYPES = ['Web App', 'Script', 'Mobile App', 'Chrome Extension']
ROLES = {
    'product_owner': ['project_description', 'user_stories', 'user_tasks'],
    'architect': ['architecture'],
    'tech_lead': ['development_planning'],
    'full_stack_developer': ['coding'],
    'dev_ops': ['environment_setup'],
    'code_monkey': ['coding']
}
STEPS = [
    'project_description',
    'user_stories',
    'user_tasks',
    'architecture',
    'environment_setup',
    'development_planning',
    'coding',
    'finished'
]

additional_ignore_folders = os.environ.get('IGNORE_FOLDERS', '').split(',')

# TODO: rename to IGNORE_PATHS as it also contains files
IGNORE_FOLDERS = [
    '.git',
    '.gpt-pilot',
    '.idea',
    '.vscode',
    '.DS_Store',
    '__pycache__',
    'node_modules',
    'package-lock.json',
    'venv',
    'dist',
    'build',
    'target'
] + [folder for folder in additional_ignore_folders if folder]

PROMPT_DATA_TO_IGNORE = {'directory_tree', 'name'}
