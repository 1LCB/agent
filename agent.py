from openai import OpenAI
from logger import log
import inspect, json
from pydantic import BaseModel
from schema import FirstStep, NextStep


class Agent:
    def __init__(self, model: str, temperature: float = 0.0, **openai_kwargs):
        self.model = model
        self.temperature = temperature
        self.tools_description = []
        self.tool_mapping = {}

        self.client = OpenAI(**openai_kwargs)
        self.conversation_history = []

    def tool(self, description: str | None = None):
        def wrapper(f):
            signature = inspect.signature(f)
            params = {
                name: {
                    "type": param.annotation.__name__ if param.annotation is not inspect.Parameter.empty else "Any",
                    "default": param.default if param.default is not inspect.Parameter.empty else None,
                    "required": False if param.default is not inspect.Parameter.empty else True
                }
                for name, param in signature.parameters.items()
            }
            return_annotation = signature.return_annotation
            
            if return_annotation is None:
                return_type = "null"
            else:
                return_type = return_annotation.__name__ if return_annotation is not inspect.Signature.empty else "Any"

            tool_info = {
                "name": f.__name__,
                "doc": description or f.__doc__,
                "parameters": params,
                "return_type": return_type
            }

            self.tools_description.append(tool_info)
            self.tool_mapping[f.__name__] = f

            return f
        return wrapper

    def describe_functions(self) -> str:
        return json.dumps(self.tools_description, indent=4)

    def run(self, task: str, instructions: str | None = None) -> str:
        log.green("TASK", task)

        system = f"You are a helpful AI assistant that breaks down tasks into steps and solves them systematically.\n\nYou have access to these tools: {self.describe_functions()}.\n\nIf you already know the answer, just say it."
        if instructions:
            system += f"\n\nYour Instructions:\n{instructions}"

        self.conversation_history = [
            {"role": "system", "content": system},
            {"role": "user", "content": task}
        ]

        response = self.__call_llm(format_response=FirstStep)
        response_model = FirstStep.model_validate_json(response)
        self.conversation_history.append({"role": "assistant", "content": response_model.thought})   

        log.magenta("THOUGHT", f"{response_model.thought}")

        if response_model.execute_function:
            log.yellow("FUNCTION", f"Executing {response_model.function_name} {response_model.function_parameters}")
            self.__execute_func(response_model) 
        elif response_model.final_answer:
            return response_model.final_answer

        while True:
            response = self.__call_llm(format_response=NextStep)
            response_model = NextStep.model_validate_json(response)

            log.magenta("THOUGHT", f"{response_model.thought}")
            self.conversation_history.append({"role": "assistant", "content": response_model.thought})   

            if response_model.execute_function:
                log.yellow("FUNCTION", f"{response_model.function_name} {response_model.function_parameters}")
                self.__execute_func(response_model)
            elif response_model.final_answer:
                return response_model.final_answer

    def __execute_func(self, response_model: NextStep | FirstStep):
        result = self.tool_mapping[response_model.function_name](**json.loads(response_model.function_parameters))
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
