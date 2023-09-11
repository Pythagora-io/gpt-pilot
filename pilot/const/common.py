APP_TYPES = ['Web App', 'Script', 'Mobile App (unavailable)', 'Chrome Extension (unavailable)']
ROLES = {
    'product_owner': ['project_description', 'user_stories', 'user_tasks'],
    'architect': ['architecture'],
    'tech_lead': ['development_planning'],
    'full_stack_developer': ['create_scripts', 'coding'],
    'dev_ops': ['environment_setup'],
}
STEPS = [
    'project_description',
    'user_stories',
    'user_tasks',
    'architecture',
    'development_planning',
    'environment_setup',
    'coding'
]

IGNORE_FOLDERS = [
    '.git',
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
