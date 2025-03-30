from pydantic import BaseModel, Field
from typing import Any

class FirstStep(BaseModel):
    question: str = Field(..., description="the input question")
    thought: str = Field(..., description="your step-by-step thinking")
    execute_function: bool = Field(..., description="if necessary to execute a function")
    function_name: str = Field(..., description="the name of one of the available functions")
    function_parameters: dict[str, Any] = Field(..., description="the parameters for the action")

class NextStep(BaseModel):
    thought: str = Field(..., description="your reasoning about the result")
    execute_function: bool = Field(..., description="if necessary to execute a function")
    function_name: str = Field(..., description="the name of one of the available functions")
    function_parameters: dict[str, Any] = Field(..., description="the parameters for the function")
    final_answer: str = Field("", description="your complete answer to the question if the task is finished")