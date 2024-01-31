# utils/utils.py

import datetime
import os
import platform
import uuid
import distro
import json
import hashlib
import re
import copy
from jinja2 import Environment, FileSystemLoader
from .style import color_green

from const.llm import MAX_QUESTIONS, END_RESPONSE
from const.common import ROLES, STEPS
from logger.logger import logger

prompts_path = os.path.join(os.path.dirname(__file__), '..', 'prompts')
file_loader = FileSystemLoader(prompts_path)
env = Environment(loader=file_loader)


def capitalize_first_word_with_underscores(s):
    # Split the string into words based on underscores.
    words = s.split('_')

    # Capitalize the first word and leave the rest unchanged.
    words[0] = words[0].capitalize()

    # Join the words back into a string with underscores.
    capitalized_string = '_'.join(words)

    return capitalized_string


def get_prompt(prompt_name, original_data=None):
    data = copy.deepcopy(original_data) if original_data is not None else {}

    get_prompt_components(data)

    logger.info(f"Getting prompt for {prompt_name}")

    # Load the template
    template = env.get_template(prompt_name)

    # Render the template with the provided data
    output = template.render(data)

    return output


def get_prompt_components(data):
    # This function reads and renders all prompts inside /prompts/components and returns them in dictionary

    # Create an empty dictionary to store the file contents.
    prompts_components = {}
    data.update({
        'MAX_QUESTIONS': MAX_QUESTIONS,
        'END_RESPONSE': END_RESPONSE
    })

    # Create a FileSystemLoader
    prompts_path = os.path.join(os.path.dirname(__file__), '..', 'prompts/components')
    file_loader = FileSystemLoader(prompts_path)

    # Create the Jinja2 environment
    env = Environment(loader=file_loader)

    # Get the list of template names
    template_names = env.list_templates()

    # For each template, load and store its content
    for template_name in template_names:
        # Get the filename without extension as the dictionary key.
        file_key = os.path.splitext(template_name)[0]

        # Load the template and render it with no variables
        file_content = env.get_template(template_name).render(data)

        # Store the file content in the dictionary
        prompts_components[file_key] = file_content

    return data.update(prompts_components)


def get_sys_message(role,args=None):
    """
    :param role: 'product_owner', 'architect', 'dev_ops', 'tech_lead', 'full_stack_developer', 'code_monkey'
    :return: { "role": "system", "content": "You are a {role}... You do..." }
    """
    content = get_prompt(f'system_messages/{role}.prompt',args)

    return {
        "role": "system",
        "content": content
    }


def find_role_from_step(target):
    for role, values in ROLES.items():
        if target in values:
            return role

    return 'product_owner'


def get_os_info():
    os_info = {
        "OS": platform.system(),
        "OS Version": platform.version(),
        "Architecture": platform.architecture()[0],
        "Machine": platform.machine(),
        "Node": platform.node(),
        "Release": platform.release(),
    }

    if os_info["OS"] == "Linux":
        os_info["Distribution"] = distro.name(pretty=True)
    elif os_info["OS"] == "Windows":
        os_info["Win32 Version"] = ' '.join(platform.win32_ver())
    elif os_info["OS"] == "Mac":
        os_info["Mac Version"] = platform.mac_ver()[0]

    # Convert the dictionary to a readable text format
    return array_of_objects_to_string(os_info)


def should_execute_step(arg_step, current_step):
    """
    :param arg_step: `project.args['step']`, may be None
    :param current_step:  The step that would be executed next by the calling method.
    :return: True if `current_step` should be executed.
    """
    arg_step_index = 0 if arg_step is None else STEPS.index(arg_step) if arg_step in STEPS else None
    current_step_index = STEPS.index(current_step) if current_step in STEPS else None

    return arg_step_index is not None and current_step_index is not None and current_step_index >= arg_step_index


def step_already_finished(args, step):
    args.update(step['app_data'])

    message = f"✅  {capitalize_first_word_with_underscores(step['step'])}"
    print(color_green(message))
    logger.info(message)


def generate_app_data(args):
    return {'app_id': args['app_id'], 'app_type': args['app_type']}


def array_of_objects_to_string(array):
    return '\n'.join([f'{key}: {value}' for key, value in array.items()])


def hash_data(data):
    serialized_data = json.dumps(replace_functions(data), sort_keys=True).encode('utf-8')
    return hashlib.sha256(serialized_data).hexdigest()


def replace_functions(obj):
    if isinstance(obj, dict):
        return {k: replace_functions(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [replace_functions(item) for item in obj]
    elif callable(obj):
        return "function"
    else:
        return obj


def fix_json(s):
    s = s.replace('True', 'true')
    s = s.replace('False', 'false')
    # s = s.replace('`', '"')
    return fix_json_newlines(s)


def fix_json_newlines(s):
    pattern = r'("(?:\\\\n|\\.|[^"\\])*")'

    def replace_newlines(match):
        return match.group(1).replace('\n', '\\n')

    return re.sub(pattern, replace_newlines, s)


def clean_filename(filename):
    # Remove invalid characters
    cleaned_filename = re.sub(r'[<>:"/\\|?*]', '', filename)

    # Replace whitespace with underscore
    cleaned_filename = re.sub(r'\s', '_', cleaned_filename)

    return cleaned_filename

def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""
    if isinstance(obj, (datetime.datetime, datetime.date)):
        return obj.isoformat()
    elif isinstance(obj, uuid.UUID):
        return str(obj)
    else:
        return str(obj)

def remove_lines_with_string(file_content, matching_string):
    lines = file_content.split('\n')
    new_lines = [line for line in lines if matching_string not in line.lower()]
    return '\n'.join(new_lines)
