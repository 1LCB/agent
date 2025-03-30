# 🤖 Agent Task Executor

A flexible AI agent designed to solve one task at a time. This agent can run in standalone mode or as part of a multi-agent orchestration, enabling seamless integration into larger systems.

## ✨ Features

- **🛠️ Tool Integration:**  
  Use the `@agent.tool` decorator to easily register functions that the agent can call. Each tool's metadata (description, parameters, and return type) is automatically documented and available for the LLM to reference.

- **💬 Conversational Task Execution:**  
  The agent maintains a conversation history and interacts with an LLM to break down tasks into logical steps. It supports multiple rounds of reasoning and execution until a final answer is reached.

- **🔀 Flexible Execution Modes:**  
  Designed to be run as a standalone agent for single tasks, or orchestrated with other agents for multi-agent workflows. It is particularly suited for scenarios where a task needs to be handled step-by-step.

- **⚡ Dynamic Function Calling:**  
  Automatically executes functions based on the LLM's instructions. Results from function executions are appended to the conversation history, enabling further reasoning by the LLM.

- **🛠️ Customizable LLM Integration:**  
  The agent leverages an LLM client (e.g., OpenAI’s API) with customizable models and parameters (e.g., temperature) to suit different task complexities and interaction styles.

- **📜 Built-in Logging and Debugging:**  
  Provides clear logging for task descriptions, thoughts, function executions, and final answers, making it easy to trace and debug the decision-making process.


# Example

```py
from agent import Agent

agent = Agent(model="SOME MODEL HERE")

@agent.tool("Returns the temperature of a specific city")
def get_city_temperatures(city: str) -> str:
    return f"{city.title()} is currently at 15 degrees"

response = agent.run("what are the temperatures in Paris and Berlin?")
print(response)
```