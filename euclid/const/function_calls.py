from utils.llm import parse_llm_output

def process_user_stories(stories):
    return stories

def return_array_from_prompt(values_in_list):
    return {
        'name': 'process_user_stories',
        'description': f"Print the list of user stories that are created.",
        'parameters': {
            'type': 'object',
            "properties": {
                "stories": {
                    "type": "array",
                    "description": f"List of user stories that are created in a list.",
                    "items": {
                        "type": "string",
                        "description": "User story"
                    },
                },
            },
            "required": ["stories"],
        },
    }

USER_STORIES = {
    'definitions': [
        return_array_from_prompt('user stories')
    ],
    'functions': {
        'process_user_stories': process_user_stories
    },
}