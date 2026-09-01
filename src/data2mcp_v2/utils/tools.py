from fastmcp.tools import Tool


def function2tool(
    func: callable, name: str, description: str, func_args: dict = None
) -> Tool:
    if func_args is None:
        func_args = {}
    tool = Tool.from_function(
        func,
        name=name,
        description=description,
    )
    tool = Tool.from_tool(
        tool,
        transform_args=func_args,
    )
    return tool


def end_with_message():
    return function2tool(
        func=lambda message: message,
        name="end_with_message",
        description="End the execution with a message.",
    )
