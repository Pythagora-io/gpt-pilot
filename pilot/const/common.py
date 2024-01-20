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

DEFAULT_IGNORE_PATHS = [
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
    'target',
    "*.min.js",
    "*.min.css",
    "*.svg",
    "*.csv",
]
IGNORE_PATHS = DEFAULT_IGNORE_PATHS + [
    folder for folder
    in os.environ.get('IGNORE_PATHS', '').split(',')
    if folder
]
IGNORE_SIZE_THRESHOLD = 102400  # 100K+ files are ignored by default
PROMPT_DATA_TO_IGNORE = {'directory_tree', 'name'}
