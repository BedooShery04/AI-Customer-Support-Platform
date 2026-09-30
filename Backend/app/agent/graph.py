
import os

from langchain_core.messages import SystemMessage
from langchain_groq import ChatGroq
from langgraph.graph import (
    END,
    START,
    MessagesState,
    StateGraph,
)
from langgraph.prebuilt import ToolNode

from app.agent.prompts import AGENT_SYSTEM_PROMPT
from app.agent.tools import build_tools
from app.enums import UserRole


model = ChatGroq(
    model=os.environ["GROQ_MODEL"],
    temperature=0,
)


def build_graph(db, user_id: int,chat_id: int, user_role: UserRole,):
    agent_tools = build_tools(
        db=db,
        user_id=user_id,
        chat_id=chat_id,
        user_role=user_role,
    )

    model_with_tools = model.bind_tools(
        agent_tools
    )

    async def call_model(state: MessagesState):
        messages = [
            SystemMessage(
                content=AGENT_SYSTEM_PROMPT
            ),
            *state["messages"],
        ]

        response = await model_with_tools.ainvoke(
            messages
        )

        return {
            "messages": [response]
        }

    def should_continue(state: MessagesState):
        last_message = state["messages"][-1]

        if getattr(
            last_message,
            "tool_calls",
            None,
        ):
            return "tools"

        return END

    builder = StateGraph(MessagesState)

    builder.add_node(
        "agent",
        call_model,
    )

    builder.add_node(
        "tools",
        ToolNode(agent_tools),
    )

    builder.add_edge(
        START,
        "agent",
    )

    builder.add_conditional_edges(
        "agent",
        should_continue,
        {
            "tools": "tools",
            END: END,
        },
    )

    builder.add_edge(
        "tools",
        "agent",
    )

    return builder.compile()