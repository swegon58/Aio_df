from typing import Literal

from langchain.tools import tool
from pydantic import BaseModel, Field


class ClarificationQuestion(BaseModel):
    """A single clarification question to present to the user."""

    question: str = Field(description="The clarification question to ask the user. Be specific and clear.")
    clarification_type: Literal[
        "missing_info",
        "ambiguous_requirement",
        "approach_choice",
        "risk_confirmation",
        "suggestion",
    ] = Field(description="The type of clarification needed.")
    context: str | None = Field(
        default=None,
        description="Optional context explaining why this clarification is needed.",
    )
    options: list[str] | None = Field(
        default=None,
        description="Optional list of choices (for approach_choice or suggestion types).",
    )


@tool("ask_clarification", parse_docstring=True, return_direct=True)
def ask_clarification_tool(questions: list[ClarificationQuestion]) -> str:
    """Ask the user for clarification when you need more information to proceed.

    Use this tool when you encounter situations where you cannot proceed without user input:

    - **Missing information**: Required details not provided (e.g., file paths, URLs, specific requirements)
    - **Ambiguous requirements**: Multiple valid interpretations exist
    - **Approach choices**: Several valid approaches exist and you need user preference
    - **Risky operations**: Destructive actions that need explicit confirmation (e.g., deleting files, modifying production)
    - **Suggestions**: You have a recommendation but want user approval before proceeding

    The execution will be interrupted and the questions will be presented to the user, one at a
    time in the UI with the ability to navigate back and forth, before you get a single combined
    response covering every question.

    Best practices:
    - If you have more than one open question, batch them into ONE call (1-5 questions) instead
      of asking one, waiting, then asking the next. This lets the user answer everything in one
      pass instead of being interrupted repeatedly.
    - Never send more than 5 questions in a single call — trim to the most important ones.
    - Be specific and clear in each question.
    - Don't make assumptions when clarification is needed.
    - For risky operations, ALWAYS ask for confirmation.
    - After calling this tool, execution will be interrupted automatically.

    Args:
        questions: 1 to 5 clarification questions to ask the user in a single batch.
    """
    # This is a placeholder implementation
    # The actual logic is handled by ClarificationMiddleware which intercepts this tool call
    # and interrupts execution to present the questions to the user
    return "Clarification request processed by middleware"
