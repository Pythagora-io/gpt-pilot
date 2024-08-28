from typing import Optional

from pydantic import BaseModel, Field

from core.agents.base import BaseAgent
from core.agents.convo import AgentConvo
from core.agents.response import AgentResponse
from core.agents.troubleshooter import IterationPromptMixin
from core.db.models.project_state import IterationStatus
from core.llm.parser import JSONParser
from core.log import get_logger

log = get_logger(__name__)


class AlternativeSolutions(BaseModel):
    # FIXME: This is probably extra leftover from some dead code in the old implementation
    description_of_tried_solutions: str = Field(
        description="A description of the solutions that were tried to solve the recurring issue that was labeled as loop by the user.",
    )
    alternative_solutions: list[str] = Field(
        description=("List of all alternative solutions to the recurring issue that was labeled as loop by the user.")
    )


class ProblemSolver(IterationPromptMixin, BaseAgent):
    agent_type = "problem-solver"
    display_name = "Problem Solver"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.iteration = self.current_state.current_iteration
        self.next_state_iteration = self.next_state.current_iteration
        self.previous_solutions = [s for s in self.iteration["alternative_solutions"] if s["tried"]]
        self.possible_solutions = [s for s in self.iteration["alternative_solutions"] if not s["tried"]]

    async def run(self) -> AgentResponse:
        if self.iteration is None:
            log.warning("ProblemSolver agent started without an iteration to work on, possible bug?")
            return AgentResponse.done(self)

        if not self.possible_solutions:
            await self.generate_alternative_solutions()
            return AgentResponse.done(self)

        return await self.try_alternative_solutions()

    async def generate_alternative_solutions(self):
        llm = self.get_llm(stream_output=True)
        convo = (
            AgentConvo(self)
            .template(
                "get_alternative_solutions",
                user_input=self.iteration["user_feedback"],
                iteration=self.iteration,
                previous_solutions=self.previous_solutions,
            )
            .require_schema(AlternativeSolutions)
        )
        llm_response: AlternativeSolutions = await llm(
            convo,
            parser=JSONParser(spec=AlternativeSolutions),
            temperature=1,
        )
        self.next_state_iteration["alternative_solutions"] = self.iteration["alternative_solutions"] + [
            {
                "user_feedback": None,
                "description": solution,
                "tried": False,
            }
            for solution in llm_response.alternative_solutions
        ]
        self.next_state.flag_iterations_as_modified()

    async def try_alternative_solutions(self) -> AgentResponse:
        preferred_solution = await self.ask_for_preferred_solution()
        if preferred_solution is None:
            # TODO: We have several alternative solutions but the user didn't choose any.
            # This means the user either needs expert help, or that they need to go back and
            # maybe rephrase the tasks or even the project specs.
            # For now, we'll just mark these as not working and try to regenerate.
            self.next_state_iteration["alternative_solutions"] = [
                {
                    **s,
                    "tried": True,
                    "user_feedback": s["user_feedback"] or "That doesn't sound like a good idea, try something else.",
                }
                for s in self.possible_solutions
            ]
            self.next_state.flag_iterations_as_modified()
            return AgentResponse.done(self)

        index, next_solution_to_try = preferred_solution
        llm_solution = await self.find_solution(
            self.iteration["user_feedback"],
            next_solution_to_try=next_solution_to_try,
        )

        self.next_state_iteration["alternative_solutions"][index]["tried"] = True
        self.next_state_iteration["description"] = llm_solution
        self.next_state_iteration["attempts"] = self.iteration["attempts"] + 1
        self.next_state_iteration["status"] = IterationStatus.PROBLEM_SOLVER
        self.next_state.flag_iterations_as_modified()
        return AgentResponse.done(self)

    async def ask_for_preferred_solution(self) -> Optional[tuple[int, str]]:
        solutions = self.possible_solutions
        buttons = {}

        for i in range(len(solutions)):
            buttons[str(i)] = str(i + 1)
        buttons["none"] = "None of these"

        solutions_txt = "\n\n".join([f"{i+1}: {s['description']}" for i, s in enumerate(solutions)])
        user_response = await self.ask_question(
            "Choose which solution would you like Pythagora to try next:\n\n" + solutions_txt,
            buttons=buttons,
            default="0",
            buttons_only=True,
        )
        if user_response.button == "none" or user_response.cancelled:
            return None

        try:
            i = int(user_response.button)
            return i, solutions[i]
        except (ValueError, IndexError):
            return None
