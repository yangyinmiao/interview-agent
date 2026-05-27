"""Agent tool functions shared across agents."""

from langchain_core.tools import tool


@tool
def parse_json_response(response: str) -> dict:
    """Parse a JSON string response from LLM into a dict."""
    import json
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        return {"raw": response, "error": "invalid_json"}


@tool
def format_conversation_history(messages: list[dict]) -> str:
    """Format conversation history into readable text."""
    lines = []
    for i, msg in enumerate(messages):
        role = "面试官" if msg.get("role") == "interviewer" else "候选人"
        lines.append(f"第{i+1}轮 - {role}: {msg.get('content', '')}")
    return "\n\n".join(lines)
