"""
Helper functions for agents
"""
from typing import List
from langchain_core.messages import AIMessage
from models import AgentState


def last_ai_text(messages: List) -> str:
    """Get the text of the last AI message from the history"""
    for msg in reversed(messages):
        if isinstance(msg, AIMessage):
            return msg.content.strip()
    return ""


def on_step_logger(tag: str, state: AgentState) -> None:
    """Logging the agent state on each step"""
    print("=" * 60)
    print(f"[{tag}] iter={state['iter']} needs={state['needs_revision']} score={state.get('score')}")
    print("=" * 60)