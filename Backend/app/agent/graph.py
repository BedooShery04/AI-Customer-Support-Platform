import os

from langchain_core.messages import SystemMessage
from langchain_groq import ChatGroq

from langgraph.graph import START, END, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode

from app.enums import UserRole
from app.agent.prompts import AGENT_SYSTEM_PROMPT
from app.agent.tools import build_tools


# =========================================================
# 1 Create Groq Model
# =========================================================

model = ChatGroq(
    model=os.environ["GROQ_MODEL"],
    temperature=0,
)


# =========================================================
# 2 Build Agent Graph
# =========================================================

def build_graph(
    db,
    user_id: int,
    user_role: UserRole,
):
    """
    Build the LangGraph workflow for the current user.

    db:
        Database session used by the tools.

    user_id:
        ID of the authenticated user.

    user_role:
        Role of the authenticated user.
    """

    # -----------------------------------------------------
    # Build tools for the current user
    # -----------------------------------------------------

    agent_tools = build_tools(
        db=db,
        user_id=user_id,
        user_role=user_role,
    )

    # -----------------------------------------------------
    # Give the tools to Groq
    # -----------------------------------------------------

    model_with_tools = model.bind_tools(
        agent_tools
    )

    # =====================================================
    # Agent Node
    # =====================================================

    async def call_model(state: MessagesState):
        """
        Send the conversation to Groq.
        """

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

    # =====================================================
    # Decide Next Step
    # =====================================================

    def should_continue(state: MessagesState):
        """
        Decide whether the AI wants to call a tool
        or return the final answer.
        """

        last_message = state["messages"][-1]

        # AI wants to use a tool
        if getattr(
            last_message,
            "tool_calls",
            None
        ):
            return "tools"

        # AI already produced final answer
        return END

    # =====================================================
    # Create Graph
    # =====================================================

    builder = StateGraph(
        MessagesState
    )

    # Add AI node
    builder.add_node(
        "agent",
        call_model
    )

    # Add tools node
    builder.add_node(
        "tools",
        ToolNode(agent_tools)
    )

    # START → Agent
    builder.add_edge(
        START,
        "agent"
    )

    # Agent → Tools OR END
    builder.add_conditional_edges(
        "agent",
        should_continue,
        {
            "tools": "tools",
            END: END,
        },
    )

    # Tools → Agent
    builder.add_edge(
        "tools",
        "agent"
    )

    # -----------------------------------------------------
    # Compile graph
    # -----------------------------------------------------

    return builder.compile()