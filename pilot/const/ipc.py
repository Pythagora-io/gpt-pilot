MESSAGE_TYPE = {
    'verbose': 'verbose',
    'stream': 'stream',
    'user_input_request': 'user_input_request',   # Displayed above the
    'hint': 'hint',                        # Hint text, eg "Do you want to add anything else? If not, just press ENTER."
    'info': 'info',                        # JSON data can be sent to progress `progress_stage`
    'local': 'local',
    'run_command': 'run_command',          # Command to run server needed for extension only
    'project_folder_name': 'project_folder_name',  # Project folder name for extension only
    'button': 'button',                    # Button text for extension only
    'exit': 'exit',                        # Exit message to let extension know we are done
}

LOCAL_IGNORE_MESSAGE_TYPES = [
    'info',
    'project_folder_name',
    'button',
    'exit',
]