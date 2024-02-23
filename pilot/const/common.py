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
    '.next',
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
    "*.log",
    "go.sum",
]
IGNORE_PATHS = DEFAULT_IGNORE_PATHS + [
    folder for folder
    in os.environ.get('IGNORE_PATHS', '').split(',')
    if folder
]
IGNORE_SIZE_THRESHOLD = 50000  # 50K+ files are ignored by default
PROMPT_DATA_TO_IGNORE = {'directory_tree', 'name'}


EXAMPLE_PROJECT_DESCRIPTION = (
    "A simple webchat application in node/express using MongoDB. "
    "Use Bootstrap and jQuery on the frontend, for a simple, clean UI. "
    "Use socket.io for real-time communication between backend and frontend.\n\n"
    "Visiting http://localhost:3000/, users must first log in or create an account using "
    "a username and a password (no email required).\n\n"
    "Once authenticated, on the home screen users see list of active chat rooms and a button to create a new chat. "
    "They can either click a link to one of the chat rooms which redirects them to `/<chat-id>/` "
    "or click the button to create a new chat. Creating a new chat should ask for the chat name, "
    "and then create a new chat with that name (which doesn't need to be unique), and a unique chat id. "
    "The user should then be redirected to the chat page.\n\n"
    "Chat page should have the chat name as the title. There's no possibility to edit chat name. "
    "Below that, show previous messages in the chat (these should get loaded from the database "
    "whenever the user visits the page so the user sees previous conversation in that chat - "
    "no pagination, entire history should be loaded). "
    "User has a text field and a button 'send' to send the message "
    "(pressing enter in the text field should also send the message). "
    "There's also a button to change user's nickname (default is equal to username, "
    "there's no need to store the nickname in the user's profile).\n\n"
    "Sent messages should be immediately shown to other participants in the same chat (use socket.io), "
    "and stored in the database (forever - no message expiry). "
    "All messages are text-only: no image upload, no embedding, no special markup in the messages. "
    "There's no message size limit. Also, there's no need to notify/alert user of new messages, or keep track of unread messages.\n\n"
    "All channels are available to all authenticated users, there are no private messages. "
    "Anonymous users can't see or join any chat rooms, the can only log in or create an account. "
    "No moderation, filtering or any admin functionality is required. Keep everything else as simple as possible."
)
