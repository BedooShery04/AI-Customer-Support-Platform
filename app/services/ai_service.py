from sqlalchemy.orm import Session

from langchain_core.messages import HumanMessage, AIMessage

from app.agent.graph import build_graph


class AIService:

    @staticmethod
    async def chat(
        db: Session,
        customer_id: int,
        message: str,
        history: list | None = None,
    ):
        conversation = []

        if history:
            for item in history:
                if item["role"] == "user":
                    conversation.append(
                        HumanMessage(
                            content=item["content"]
                        )
                    )

                elif item["role"] == "assistant":
                    conversation.append(
                        AIMessage(
                            content=item["content"]
                        )
                    )

        conversation.append(
            HumanMessage(
                content=message
            )
        )

        graph = build_graph(
            db=db,
            customer_id=customer_id,
        )

        result = await graph.ainvoke(
            {
                "messages": conversation
            }
        )

        messages = result.get("messages", [])

        if not messages:
            raise RuntimeError(
                "AI Agent returned no messages."
            )

        final_message = messages[-1]

        return {
            "message": final_message.content
        }