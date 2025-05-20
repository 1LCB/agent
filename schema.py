from pydantic import BaseModel, Field
from typing import Any

class FirstStep(BaseModel):
    question: str = Field(..., description="the input question")
    thought: str = Field(..., description="your step-by-step thinking")
    execute_function: bool = Field(..., description="if necessary to execute a function")
    function_name: str = Field(..., description="the name of one of the available functions")
    function_parameters: str = Field(..., description="json string containing the parameters for the function")
    final_answer: str = Field("", description="this field should only be used if the answer is obvious or it has no need for a function call")

class NextStep(BaseModel):
    thought: str = Field(..., description="Your reasoning about the last result")
    execute_function: bool = Field(..., description="Whether to call another function")
    function_name: str = Field(..., description="Name of the next function to execute")
    function_parameters: str = Field(..., description="Parameters for the function as a json string, if any")
    final_answer: str = Field(..., description="Your complete answer, once all steps are done")
