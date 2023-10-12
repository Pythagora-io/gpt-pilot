APP_TYPES = ['Web App', 'Script', 'Mobile App', 'Chrome Extension']
ROLES = {
    'product_owner': ['project_description', 'user_stories', 'user_tasks'],
    'architect': ['architecture'],
    'tech_lead': ['development_planning'],
    'full_stack_developer': ['create_scripts', 'coding'],
    'dev_ops': ['environment_setup'],
    'code_monkey': ['create_scripts', 'coding', 'implement_changes']
}
STEPS = [
    'project_description',
    'user_stories',
    'user_tasks',
    'architecture',
    'environment_setup',
    'development_planning',
    'create_scripts',
    'coding',
    'implement_changes'
]

IGNORE_FOLDERS = [
    '.git',
    '.gpt-pilot',
    '.idea',
    '.vscode',
    '__pycache__',
    'node_modules',
    'package-lock.json',
    'venv',
    'dist',
    'build',
]

PROMPT_DATA_TO_IGNORE = {'directory_tree', 'name'}
