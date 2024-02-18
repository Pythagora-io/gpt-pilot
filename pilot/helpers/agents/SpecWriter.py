from helpers.AgentConvo import AgentConvo
from helpers.Agent import Agent
from utils.files import count_lines_of_code
from utils.style import color_green_bold, color_yellow_bold
from prompts.prompts import ask_user
from const.messages import AFFIRMATIVE_ANSWERS
from utils.exit import trace_code_event


INITIAL_PROJECT_HOWTO_URL = "https://github.com/Pythagora-io/gpt-pilot/wiki/How-to-write-a-good-initial-project-description"

class SpecWriter(Agent):
    def __init__(self, project):
        super().__init__('spec_writer', project)
        self.save_dev_steps = True

    def analyze_project(self, initial_prompt):
        msg = (
            "Your project description seems a bit short. "
            "The better you can describe the project, the better GPT Pilot will understand what you'd like to build.\n\n"
            f"Here are some tips on how to better describe the project: {INITIAL_PROJECT_HOWTO_URL}\n\n"
        )
        print(color_yellow_bold(msg))
        print(color_green_bold("Let's start by refining your project idea:"))

        convo = AgentConvo(self)
        convo.construct_and_add_message_from_prompt('spec_writer/ask_questions.prompt', {})

        num_questions = 0
        skipped = False
        user_response = initial_prompt
        while True:
            llm_response = convo.send_message('utils/python_string.prompt', {
                "content": user_response,
            })
            if not llm_response:
                continue

            num_questions += 1
            llm_response = llm_response.strip()
            if len(llm_response) > 500:
                print('continue', type='button')
                user_response = ask_user(
                    self.project,
                    "Can we proceed with this project description? If so, just press ENTER. Otherwise, please tell me what's missing or what you'd like to add.",
                    hint="Does this sound good, and does it capture all the information about your project?",
                    require_some_input=False
                )
                if user_response:
                    user_response = user_response.strip()
                if user_response.lower() in AFFIRMATIVE_ANSWERS + ['continue']:
                    break
            else:
                print('skip questions', type='button')
                user_response = ask_user(self.project, llm_response)
                if user_response and user_response.lower() == 'skip questions':
                    llm_response = convo.send_message(
                        'utils/python_string.prompt',
                        {
                            'content': 'This is enough clarification, you have all the information. Please output the spec now, without additional comments or questions.',
                        }
                    )
                    skipped = True
                    break

        trace_code_event(
            "spec-writer-questions",
            {
                "initial_prompt_length": len(initial_prompt),
                "num_questions": num_questions,
                "final_prompt_length": len(llm_response),
                "skipped": skipped,
            }
        )

        return llm_response


    def review_spec(self, initial_prompt, spec):
        convo = AgentConvo(self, temperature=0)
        llm_response = convo.send_message('spec_writer/review_spec.prompt', {
            "brief": initial_prompt,
            "spec": spec,
        })
        if not llm_response:
            return None
        return llm_response.strip()

    def create_spec(self, initial_prompt):
        if len(initial_prompt) > 1500:
            return initial_prompt

        spec = self.analyze_project(initial_prompt)
        missing_info = self.review_spec(initial_prompt, spec)
        if missing_info:
            spec += "\nAdditional info/examples:\n" + missing_info

        return spec
