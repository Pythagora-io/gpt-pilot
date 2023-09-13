from helpers.Agent import Agent
from helpers.AgentConvo import AgentConvo
from const.function_calls import ROUTE_INITIAL_INPUT


class Receptionist(Agent):
    def __init__(self, project):
        super().__init__('receptionist', project)
        self.convo = AgentConvo(self)

    def route_initial_input(self, user_input: str):
        route = self.convo.send_message('routing/route_initial_input.prompt',
                                   {'input': user_input},
                                   ROUTE_INITIAL_INPUT)
        return route
