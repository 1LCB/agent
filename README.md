# Tiny Agent Framework

## Overview
A lightweight AI agent framework featuring tool calling, streaming responses, and hooks. Designed for simplicity and flexibility.

The framework operates through iterative (reAct) problem-solving by calling available tools. When no further tools are needed, it returns the final response.

## Features
- Dynamic system prompt composition
- Automatic tool schema generation via decorators
- Minimal dependencies (OpenAI library only)
- Dependency injection through tools and hooks
- Conversation history management
- Streaming response support

## Quick Example

```python
from agent import Agent
from datetime import datetime

SYSTEM_PROMPT = """
You are a helpful AI assistant. 
"""

def read_file(file_path: str) -> str:
    """
    Reads and returns the contents of a file at the given file path.
    
    Args:
        file_path (str): The path to the file to read
        
    Returns:
        str: The file contents if successful, or an error message if the operation fails
    """
    try:
        with open(file_path, "r") as file:
            return file.read()
    except Exception as exc:
        return f"Error reading file: {exc}"

# Initialize the agent with Gemini model configuration
agent = Agent(
    model="gemini-2.5-flash",
    system_prompt=SYSTEM_PROMPT,
    api_key="xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
    tools=[read_file]  # Pre-register read_file as a tool
)

@agent.tool()
def write_file(file_path: str, content: str) -> str:
    """
    Writes content to a file at the specified file path.
    
    Args:
        file_path (str): The path where the file will be created/overwritten
        content (str): The content to write into the file
        
    Returns:
        str: Success message if writing succeeds, or an error message if it fails
    """
    try:
        with open(file_path, "w") as file:
            file.write(content)
            return f"Successfully wrote {len(content)} characters to {file_path}"
    except Exception as exc:
        return f"Error writing to file: {exc}"
    
@agent.system_prompt()
def get_current_datetime():
    now = datetime.now()
    # This will be appended to the system prompt
    # every time run_stream() is called
    return f"Current datetime: {now.isoformat()}"

if __name__ == "__main__":
    prompt = "Write a Python function that outputs 'hello world' inside a file named script.py"
    
    print("Agent response:")
    for chunk in agent.run_stream(prompt):
        print(chunk, end="", flush=True)
```

## Example using Dependency Injection
```python
from agent import Agent
from dataclasses import dataclass

@dataclass
class UserData:
    id: int
    name: str
    language: str
    session_id: str

agent = Agent(
    model="gpt-4",
    system_prompt="You are a helpful AI assistant that personalizes responses based on user context.",
)
    
@agent.system_prompt()
def get_current_user_information(ctx: UserData) -> str:
    """
    Injects current user information into the system prompt.
    """
    return f"""
Current User Context:
- User ID: {ctx.id}
- Name: {ctx.name}
- Preferred Language: {ctx.language}
- Session ID: {ctx.session_id}

Please tailor your responses to this user's context and speak in their preferred language when appropriate.
"""

@agent.tool()
def get_user_orders(ctx: UserData, status_filter: str = "all") -> str:
    """
    Retrieves user's orders filtered by status.
    """
    # In a real application, this would query a database
    return f"Retrieved {status_filter} orders for user {ctx.name} (ID: {ctx.id}): [Order1, Order2, Order3]"

@agent.tool()
def get_user_preferences(ctx: UserData) -> str:
    """
    Gets the current user's preferences and settings.
    """
    return f"""
User Preferences for {ctx.name}:
- Language: {ctx.language}
- Theme: Dark mode
- Notifications: Enabled
- Timezone: America/Sao_Paulo
"""

if __name__ == "__main__":
    user_context = UserData(
        id=1,
        name="Lucas",
        language="Brazilian Portuguese", 
        session_id="sess_abc123xyz"
    )
    
    prompt = "What do you know about me and can you show my recent orders?"
    print("Agent: ", end="")
    for chunk in agent.run_stream(prompt, dependency=user_context):
        print(chunk, end="", flush=True)
    print("\n")
```

## Disclaimer ⚠️
This project is primarily a proof-of-concept for building AI agents from scratch using Python and the OpenAI-compatible API. While functional, it may not be suitable for production environments without modifications.

Key limitations include:
- Basic error handling
- Limited memory management capabilities
- No asynchronous support
- Minimal logging infrastructure
- Static tool registration

You are encouraged to adapt and extend the code according to your needs. The framework has been tested primarily with Gemini Flash and OpenRouter models; other OpenAI-compatible providers may require code adjustments.