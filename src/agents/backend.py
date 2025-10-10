from langgraph.graph.message import add_messages, AnyMessage
from langchain_core.messages import convert_to_messages
from langgraph.graph.state import CompiledStateGraph
from langchain_core.messages import ToolMessage
from IPython.display import Image
from pyprojroot import here

from typing_extensions import TypedDict
from typing import Annotated, Literal
import json


class State(TypedDict):
    """Represents the state structure containing a list of messages.

    Attributes:
        messages (list): A list of messages, where each message can be processed
        by adding messages using the `add_messages` function.
    """
    messages: Annotated[list, add_messages]


class BasicToolNode:
    """A node that runs the tools requested in the last AIMessage.

    This class retrieves tool calls from the most recent AIMessage in the input
    and invokes the corresponding tool to generate responses.

    Attributes:
        tools_by_name (dict): A dictionary mapping tool names to tool instances.
    """

    def __init__(self, tools: list) -> None:
        """Initializes the BasicToolNode with available tools.

        Args:
            tools (list): A list of tool objects, each having a `name` attribute.
        """
        self.tools_by_name = {tool.name: tool for tool in tools}

    def __call__(self, inputs: dict):
        """Executes the tools based on the tool calls in the last message.

        Args:
            inputs (dict): A dictionary containing the input state with messages.

        Returns:
            dict: A dictionary with a list of `ToolMessage` outputs.

        Raises:
            ValueError: If no messages are found in the input.
        """
        if messages := inputs.get("messages", []):
            message: AnyMessage = messages[-1]
        else:
            raise ValueError("No message found in input")
        outputs = []
        for tool_call in message.tool_calls:
            tool_result = self.tools_by_name[tool_call["name"]].invoke(tool_call["args"])

            outputs.append(
                ToolMessage(
                    content=json.dumps(tool_result),
                    name=tool_call["name"],
                    tool_call_id=tool_call["id"],
                )
            )
        print(outputs)
        return {"messages": outputs}


def route_tools(state: State) -> Literal["tools", "__end__"]:
    """
    Determines whether to route to the ToolNode or end the flow.

    This function is used in the conditional_edge and checks the last message in the state for tool calls. If tool
    calls exist, it routes to the 'tools' node; otherwise, it routes to the end.

    Args:
        state (State): The input state containing a list of messages.

    Returns:
        Literal["tools", "__end__"]: Returns 'tools' if there are tool calls;
        '__end__' otherwise.

    Raises:
        ValueError: If no messages are found in the input state.
    """
    if isinstance(state, list):
        ai_message = state[-1]
    elif messages := state.get("messages", []):
        ai_message = messages[-1]
    else:
        raise ValueError(
            f"No messages found in input state to tool_edge: {state}")
    if hasattr(ai_message, "tool_calls") and len(ai_message.tool_calls) > 0:
        return "tools"
    return "__end__"


def plot_agent_schema(graph: CompiledStateGraph):
    """Plots the agent schema using a graph object, if possible.

    Tries to display a visual representation of the agent's graph schema
    using Mermaid format and IPython's display capabilities. If the required
    dependencies are missing, it catches the exception and prints a message
    instead.

    Args:
        graph: A graph object that has a `get_graph` method, returning a graph
        structure that supports Mermaid diagram generation.

    Returns:
        None
    """
    try:
        output_path = here("images/final_graph.png")
        graph.get_graph().draw_mermaid_png(output_file_path=output_path)
    except Exception:
        return print("Graph could not be displayed.")


def pretty_print_message(message, indent=False):
    pretty_message = message.pretty_repr(html=True)
    if not indent:
        print(pretty_message)
        return

    indented = "\n".join("\t" + c for c in pretty_message.split("\n"))
    print(indented)


def pretty_print_messages(update, last_message=False):
    is_subgraph = False
    if isinstance(update, tuple):
        ns, update = update
        # skip parent graph updates in the printouts
        if len(ns) == 0:
            return

        graph_id = ns[-1].split(":")[0]
        print(f"Update from subgraph {graph_id}:")
        print("\n")
        is_subgraph = True

    for node_name, node_update in update.items():
        update_label = f"Update from node {node_name}:"
        if is_subgraph:
            update_label = "\t" + update_label

        print(update_label)
        print("\n")

        messages = convert_to_messages(node_update["messages"])
        if last_message:
            messages = messages[-1:]

        for m in messages:
            pretty_print_message(m, indent=is_subgraph)
        print("\n")
