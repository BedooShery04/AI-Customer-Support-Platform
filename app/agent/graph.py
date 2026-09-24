import os

from langchain_core.messages import SystemMessage
from langchain_groq import ChatGroq

from langgraph.graph import START, END, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode

from app.agent.prompts import AGENT_SYSTEM_PROMPT
from app.agent.tools import build_tools


# =========================================================
# 1) Create the LLM
# =========================================================

model = ChatGroq(
    model=os.environ["GROQ_MODEL"],
    temperature=0,
)


# =========================================================
# 2) Build the Agent Graph
# =========================================================

def build_graph(db, customer_id: int):
    """
    Build the LangGraph workflow for the current customer.

    The database session and customer_id are provided by
    the application, not by the LLM.
    """

    # Build tools for the current user
    agent_tools = build_tools(
        db=db,
        customer_id=customer_id,
    )

    # Bind tools to the LLM
    model_with_tools = model.bind_tools(agent_tools)

    # =====================================================
    # 3) Agent Node
    # =====================================================

    def call_model(state: MessagesState):
        """
        Send the conversation to the LLM.

        The model receives:
        - system instructions
        - conversation history
        - available tools
        """

        messages = [
            SystemMessage(content=AGENT_SYSTEM_PROMPT),
            *state["messages"],
        ]

        response = model_with_tools.invoke(messages)

        return {
            "messages": [response]
        }

    # =====================================================
    # 4) Decide where to go next
    # =====================================================

    def should_continue(state: MessagesState):
        """
        Decide whether the LLM wants to call a tool
        or has already generated the final answer.
        """

        last_message = state["messages"][-1]

        if getattr(last_message, "tool_calls", None):
            return "tools"

        return END

    # =====================================================
    # 5) Build the Graph
    # =====================================================

    builder = StateGraph(MessagesState)

    # Agent / LLM node
    builder.add_node("agent", call_model)

    # Tool execution node
    builder.add_node(
        "tools",
        ToolNode(agent_tools)
    )

    # Start -> Agent
    builder.add_edge(
        START,
        "agent"
    )

    # Agent -> Tools OR END
    builder.add_conditional_edges(
        "agent",
        should_continue,
        {
            "tools": "tools",
            END: END,
        },
    )

    # After executing tools -> Agent
    builder.add_edge(
        "tools",
        "agent"
    )

    # =====================================================
    # 6) Compile the Graph
    # =====================================================

    return builder.compile()