import os

from langchain_core.messages import SystemMessage, ToolMessage
from langchain_groq import ChatGroq

from langgraph.graph import START, END, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode

from app.enums import UserRole
from app.agent.prompts import AGENT_SYSTEM_PROMPT
from app.agent.tools import build_tools


# =========================================================
# Groq Model
# =========================================================

model = ChatGroq(
    model=os.environ["GROQ_MODEL"],
    temperature=0,
)


# =========================================================
# Build Agent Graph
# =========================================================

def build_graph(
    db,
    user_id: int,
    user_role: UserRole,
):
    """
    Build the LangGraph workflow for the current user.

    Args:
        db: Database session used by the tools.
        user_id: ID of the authenticated user.
        user_role: Role of the authenticated user.
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
    # Bind tools to the AI model
    # -----------------------------------------------------

    model_with_tools = model.bind_tools(agent_tools)

    # =====================================================
    # Agent Node
    # =====================================================

    async def call_model(state: MessagesState):
        """
        Send the conversation to Groq and get the AI response.
        """

        messages = [
            SystemMessage(content=AGENT_SYSTEM_PROMPT),
            *state["messages"],
        ]

        response = await model_with_tools.ainvoke(messages)

        return {
            "messages": [response]
        }

    # =====================================================
    # Escalation Node
    # =====================================================

    async def escalation_node(state: MessagesState):
        """
        Handle ticket escalation when escalation is requested.
        """

        last_message = state["messages"][-1]
        tool_calls = getattr(last_message, "tool_calls", None)

        if not tool_calls:
            return {"messages": []}

        escalation_call = next(
            (
                tool_call
                for tool_call in tool_calls
                if tool_call["name"] == "escalate_ticket"
            ),
            None,
        )

        if not escalation_call:
            return {"messages": []}

        ticket_id = escalation_call["args"].get("ticket_id")

        if not ticket_id:
            return {
                "messages": [
                    ToolMessage(
                        content="Ticket ID is required for escalation.",
                        tool_call_id=escalation_call["id"],
                    )
                ]
            }

        escalation_tool = next(
            tool
            for tool in agent_tools
            if tool.name == "escalate_ticket"
        )

        result = escalation_tool.invoke(
            {
                "ticket_id": ticket_id,
            }
        )

        return {
            "messages": [
                ToolMessage(
                    content=str(result),
                    tool_call_id=escalation_call["id"],
                )
            ]
        }

    # =====================================================
    # Routing
    # =====================================================

    def should_continue(state: MessagesState):
        """
        Decide which node should handle the next step.
        """

        last_message = state["messages"][-1]
        tool_calls = getattr(last_message, "tool_calls", None)

        if not tool_calls:
            return END

        for tool_call in tool_calls:
            if tool_call["name"] == "escalate_ticket":
                return "escalation"

        return "tools"

    # =====================================================
    # Create Graph
    # =====================================================

    builder = StateGraph(MessagesState)

    # -----------------------------------------------------
    # Nodes
    # -----------------------------------------------------

    builder.add_node(
        "agent",
        call_model,
    )

    builder.add_node(
        "tools",
        ToolNode(agent_tools),
    )

    builder.add_node(
        "escalation",
        escalation_node,
    )

    # -----------------------------------------------------
    # START → Agent
    # -----------------------------------------------------

    builder.add_edge(
        START,
        "agent",
    )

    # -----------------------------------------------------
    # Agent → Tools / Escalation / END
    # -----------------------------------------------------

    builder.add_conditional_edges(
        "agent",
        should_continue,
        {
            "tools": "tools",
            "escalation": "escalation",
            END: END,
        },
    )

    # -----------------------------------------------------
    # Tools → Agent
    # -----------------------------------------------------

    builder.add_edge(
        "tools",
        "agent",
    )

    # -----------------------------------------------------
    # Escalation → Agent
    # -----------------------------------------------------

    builder.add_edge(
        "escalation",
        "agent",
    )

    # -----------------------------------------------------
    # Compile
    # -----------------------------------------------------

    return builder.compile()