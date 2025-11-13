from typing import get_args, get_origin, Literal
from openai import OpenAI
import inspect, json

class HookTypes:
    SYSTEM_PROMPT = "SYSTEM_PROMPT"
    BEFORE_AGENT_RESPONSE = "BEFORE_AGENT_RESPONSE"
    AFTER_AGENT_RESPONSE = "AFTER_AGENT_RESPONSE"

class HookFunctions:
    def __init__(self, func):
        self.func = func

    def __get_parameters(self):
        return inspect.signature(self.func).parameters
    
    def call(self, **params):
        filtered_params = {
            k: v for k, v in params.items() 
            if k in self.__get_parameters()
        }
        return self.func(**filtered_params)

class ConversationRoles:
    SYSTEM = "system"
    ASSISTANT = "assistant"
    USER = "user"
    TOOL = "tool"

class Agent:
    """
    A small AI agent framework for building conversational agents with tool calling capabilities.
    
    Features:
    - Tool registration with automatic schema generation from function signatures
    - Dynamic system prompt composition with context injection
    - Streaming responses with real-time tool execution
    - Conversation history management with export/import capabilities
    - Support for complex parameter types (Literal, list, dict)
    - Context dependency injection for tools and system prompts
    - Customizable Agent Hooks
    """

    def __init__(self, model: str, system_prompt: str, tools: list = [], **openai_kwargs):
        self.model = model
        self.tool_mapping = {}
        self.tools_schema = []

        self.hooks: dict[HookTypes, HookFunctions] = {}

        self.llm_system_prompt = system_prompt
        self.client = OpenAI(**openai_kwargs)
        self.conversation_history = [{"role": ConversationRoles.SYSTEM, "content": self.llm_system_prompt}]

        for tool in tools:
            self.__store_tool_info(tool)

    def __store_tool_info(self, f):
        has_context = self.__has_parameter_ctx_on_func(f)
        self.tool_mapping[f.__name__] = {
            "func": f,
            "hasContext": has_context,
        }

        tool_schema = self.__extract_tool_schema(f)
        self.tools_schema.append(tool_schema)

    def __extract_tool_schema(self, f):
        type_map = {
            "str": "string",
            "int": "integer",
            "float": "number",
            "bool": "boolean",
        }
        
        signature = inspect. signature(f)
        parameters = {}
        required = []

        for name, param in signature.parameters.items():
            if name == "ctx":
                continue # skip context parameter in schema
            
            annotation = param.annotation
            annotation_values = get_args(annotation)

            param_schema = {}
            # enums
            if get_origin(annotation) is Literal:
                param_schema["type"] = "string"
                param_schema["enum"] = list(get_args(annotation))
            # lists
            elif get_origin(annotation) is list:
                items_type = getattr(annotation_values[0], '__name__', str(annotation)).lower() if annotation_values else "string"
                items_type = type_map.get(items_type, "string")

                param_schema["type"] = "array"
                param_schema["items"] = {"type": items_type}
            # objects
            elif get_origin(annotation) is dict:
                annotation_values = get_args(annotation)
                items_type = getattr(annotation_values[1], '__name__', str(annotation)).lower() if len(annotation_values) == 2 else "string"
                items_type = type_map.get(items_type, "string")

                param_schema["type"] = "object"
                param_schema["additionalProperties"] = {"type": items_type}
            elif annotation is not inspect.Parameter.empty:
                param_type_name = getattr(annotation, '__name__', str(annotation)).lower()
                param_schema["type"] = type_map.get(param_type_name, "string")
            else:
                param_schema["type"] = "string"

            if param.default is inspect.Parameter.empty:
                required.append(name)
            
            parameters[name] = param_schema

        tool_schema = {
            "type": "function",
            "function": {
                "name": f.__name__,
                "description": inspect.getdoc(f),
                "parameters": {
                    "type": "object",
                    "properties": parameters,
                    "required": required,
                },
            },
        }
        return tool_schema

    def tool(self):
        def wrapper(f):
            self.__store_tool_info(f)
            return f
        return wrapper

    def __has_parameter_ctx_on_func(self, func) -> bool:
        signature = inspect.signature(func)
        return "ctx" in signature.parameters

    def before_agent_response_hook(self):
        def wrapper(f):
            self.hooks[HookTypes.BEFORE_AGENT_RESPONSE] = HookFunctions(f)

            return f
        return wrapper
    
    def after_agent_response_hook(self):
        def wrapper(f):
            self.hooks[HookTypes.AFTER_AGENT_RESPONSE] = HookFunctions(f)

        return wrapper
        
    def system_prompt(self):
        def wrapper(func):
            self.hooks[HookTypes.SYSTEM_PROMPT] = HookFunctions(func)

            return func
        return wrapper

    def clear_history(self) -> None:
        self.conversation_history = [{"role": ConversationRoles.SYSTEM, "content": self.llm_system_prompt}]

    def run_stream(
        self, 
        prompt: str, 
        dependency=None, 
        temperature: float = 0.3,
        clear_history_after_execution: bool = True, 
        max_steps: int = 30,
        **kwargs
    ):
        if clear_history_after_execution:
            self.clear_history()

        system_prompt = self.__format_system_prompt(dependency, self.llm_system_prompt).strip()
        print(system_prompt)
        if system_prompt:
            self.conversation_history[0]["content"] = system_prompt
        self.__append_message(ConversationRoles.USER, prompt) 

        # agent Loop
        logical_steps = 0
        while logical_steps < max_steps:
            logical_steps += 1

            stream = self.generate_stream_completion(
                conversation=self.conversation_history,
                temperature=temperature,
                tools=self.tools_schema if self.tools_schema else None,
                tool_choice="auto" if self.tools_schema else None,
                **kwargs
            )

            response_message = ""
            tool_calls_aggregator = []

            # yield response
            for chunk in stream:
                content_delta = chunk.choices[0].delta.content
                if content_delta:
                    response_message += content_delta
                    yield content_delta

                tool_call_chunks = chunk.choices[0].delta.tool_calls
                if tool_call_chunks:
                    # due to gemini 2.5 flash parallel tool calls
                    tool_calls_aggregator.extend(tool_call_chunks)

            self.__append_message(ConversationRoles.ASSISTANT, response_message, tool_calls_aggregator)

            if not tool_calls_aggregator:
                break # final answer

            # tool executions
            for tool_call in tool_calls_aggregator:
                tool_name = tool_call.function.name
                tool_args = tool_call.function.arguments
                tool_id = tool_call.id

                output = self.__execute_func(tool_name, tool_args, dependency)

                self.conversation_history.append({
                    "role": ConversationRoles.TOOL,
                    "tool_call_id": tool_id,
                    "name": tool_name,
                    "content": str(output),
                })

    def __call_hook(self, hook_type: HookTypes, **params):
        hook = self.hooks.get(hook_type)
        if not hook:
            return None
        return hook.call(**params)

    def __format_system_prompt(self, dependency, base_prompt: str):
        output = self.__call_hook(HookTypes.SYSTEM_PROMPT, ctx=dependency)
        if not output: 
            return base_prompt

        base_prompt += "\n" + output
        return base_prompt

    def __execute_func(self, tool_name: str, tool_parameters_str: str, dependency=None):
        func_data = self.tool_mapping.get(tool_name)
        if not func_data:
            return f"Error: Tool '{tool_name}' not found."

        func = func_data["func"]
        has_context = func_data["hasContext"]
        try:
            params = json.loads(tool_parameters_str)
            result = func(**params, ctx=dependency) if has_context else func(**params)
            return result
        except json.JSONDecodeError:
            return "Error: Invalid JSON arguments provided."
        except Exception as e:
            return f"Error executing tool '{tool_name}': {e}"

    def generate_stream_completion(self, conversation: list, temperature: float, **kwargs):
        completion = self.client.chat.completions.create(
            model=self.model,
            messages=conversation,
            temperature=temperature,
            stream=True,
            stream_options={"include_usage": True},
            **kwargs,
        )
        return completion

    def __append_message(self, role: str, content: str | None, tool_calls=None) -> None:
        message = {"role": role, "content": content}
        if tool_calls:
            message["tool_calls"] = [tool_call.model_dump() for tool_call in tool_calls]
            message["content"] = None
        self.conversation_history.append(message)

    def export_conv(self, include_system_prompt: bool = False, include_tool_calls: bool = True) -> list[dict]:
        conv = self.conversation_history.copy()
        if not include_tool_calls:
            conv = [msg for msg in conv if msg["role"] != ConversationRoles.TOOL]
        if not include_system_prompt:
            del conv[0]
        return conv

    def load_conv(self, conv: list):
        self.clear_history()
        self.conversation_history.extend(conv)
