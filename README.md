# 🤖 Agent Task Executor

A flexible and extensible AI agent designed to perform one task at a time through reasoning and function execution. Ideal for both standalone use and integration within multi-agent systems, this agent leverages LLMs to dynamically analyze tasks, call tools, and produce final answers in a conversational loop.

---

## ✨ Key Features

### 🛠️ Tool Integration with Dependency Injection

- Register tools using the `@agent.tool()` decorator.
- Automatic function signature parsing: parameter types, optionality, and return types are extracted and documented for the LLM.
- Tools can optionally receive a context object (e.g., user/session info) via dependency injection.

### 🧠 Dynamic System Prompts

- Create custom system prompts with `@agent.system_prompt()`.
- Supports dynamic content (e.g. user locale or preferences) using context-aware injections.

### 🔁 Multi-Step Conversational Execution

- Tasks are broken down into logical reasoning steps.
- The agent interacts with the LLM in a loop: think → act (function call) → observe → reason → answer.
- Results from function calls are appended to conversation history for iterative improvement.

### 🔀 Flexible Modes

- Run as a standalone agent to solve a single user request.
- Easily orchestrate with other agents in multi-agent workflows.
- Tools can also be registered externally and passed to the Agent constructor.

### 🧠 LLM Orchestration & Control

- Pluggable LLM client (OpenAI by default) with model selection and parameters (e.g., temperature).

### ⚙️ Built-in Function Metadata Introspection

- Tools are self-documented and described to the LLM.
- Supports automatic documentation of parameters, types, and return types.


# Code Example

```py
from agent import Agent
from dataclasses import dataclass

# Dependency class
@dataclass
class UserInfo:
    id: int
    name: str
    language: str


agent = Agent(
    model=""
)

@agent.system_prompt()
def custom_system_prompt(ctx: UserInfo) -> str: # the dependency here is optional
    return f"The user language is: {ctx.language}. ALWAYS respond the user using their language."


# you can create tools with dependencies
@agent.tool()
def get_user_info(ctx: UserInfo) -> str:
    """Return some information from the user you are talking to"""
    return f"""
User's id: {ctx.id}
User's name: {ctx.name}
"""

# and tools with no dependencies at all
@agent.tool()
def get_city_temperature(city_name: str) -> float:
    """Return the temperature of the given city"""
    return 25.0

# intializing the dependency class
deps = UserInfo(42, "Lucas", "PT-BR")

stream = agent.run("Hello, how are you doing?", dependency=deps)
for content in stream:
    print(content.get("type"), content.get("content"))
```