from openai import OpenAI
from logger import log
import inspect, json
from pydantic import BaseModel
from schema import FirstStep, NextStep
from prompts import DEFAULT_AGENT_INSTRUCTIONS_PROMPT

class Agent:
    def __init__(self, model: str, tools: list = [], temperature: float = 0.3, **openai_kwargs):
        self.model = model
        self.temperature = temperature
        self.tool_mapping = {}
        self.system_prompt_funcs = {}

        self.client = OpenAI(**openai_kwargs)
        self.conversation_history = []

        for tool in tools:
            self.__store_tool_info(tool)

    def __store_tool_info(self, f):
        has_context, tool_info = self.__extract_func_info(f)
        self.tool_mapping[f.__name__] = {
            "func": f,
            "hasContext": has_context,
            "info": tool_info
        }

    def __extract_func_info(self, f):
        signature = inspect.signature(f)
        params = {
            name: {
                "type": param.annotation.__name__ if param.annotation is not inspect.Parameter.empty else "Any",
                "default": param.default if param.default is not inspect.Parameter.empty else None,
                "required": False if param.default is not inspect.Parameter.empty else True
            }
            for name, param in signature.parameters.items()
        }

        has_context = bool(params.get("ctx"))
        if has_context:
            del params["ctx"] # context / dependency

        return_annotation = signature.return_annotation
        return_type = return_annotation.__name__ if return_annotation is not inspect.Signature.empty else "Any"

        tool_info = {
            "name": f.__name__,
            "doc": f.__doc__,
            "parameters": params,
            "return_type": return_type
        }
        
        return has_context, tool_info

    def tool(self):
        def wrapper(f):
            self.__store_tool_info(f)
        return wrapper
    
    def system_prompt(self):
        def wrapper(f):
            has_context, _ = self.__extract_func_info(f)
            self.system_prompt_funcs[f.__name__] = {"func": f, "hasContext": has_context}
        return wrapper

    def describe_functions(self) -> str:
        return json.dumps([i["info"] for i in self.tool_mapping.values()])

    def run(self, task: str, dependency = None, only_final_answer: bool = True):
        system = DEFAULT_AGENT_INSTRUCTIONS_PROMPT + self.describe_functions()
        if self.system_prompt_funcs:
            system = self.__format_system_prompt(dependency, system)

        self.conversation_history = [
            {"role": "system", "content": system},
            {"role": "user", "content": task}
        ]

        # agent infinite loop
        while True:
            response = self.__call_llm(format_response=NextStep)
            response_model = NextStep.model_validate_json(response)

            yield {"type": "thinking", "content": response_model.thought}

            self.conversation_history.append({"role": "assistant", "content": response_model.thought})

            if response_model.execute_function:
                log.yellow("FUNCTION", f"{response_model.function_name} {response_model.function_parameters}")
                self.__execute_func(response_model, dependency)
            elif response_model.final_answer:
                yield {"type": "final", "content": response_model.final_answer}
                break


    def __format_system_prompt(self, dependency, system):
        system += "\n\nAdditional Instructions:"
        for f in self.system_prompt_funcs.values():
            func = f["func"]
            has_context = f["hasContext"]
            output = func(ctx=dependency) if has_context else func()

            system += "\n" + output
        return system

    def __execute_func(self, response_model: NextStep | FirstStep, dependency = None):
        func_data = self.tool_mapping[response_model.function_name]

        func = func_data["func"]
        has_context = func_data["hasContext"]

        params = json.loads(response_model.function_parameters)
        result = func(**params, ctx=dependency) if has_context else func(**params)

        self.conversation_history.append(
            {
                "role": "user", 
                "content": f"Function Executed: {response_model.function_name}\nParameters: {response_model.function_parameters}\nResult: {result}"
            }
        )

    def __call_llm(self, format_response: BaseModel | None = None) -> str:
        completion = self.client.beta.chat.completions.parse(
            model=self.model,
            messages=self.conversation_history,
            response_format=format_response,
            temperature=self.temperature
        )
        return completion.choices[0].message.content
