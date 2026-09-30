from pydantic import BaseModel, Field

class ProposedTicket(BaseModel):
    subject: str = Field(
        min_length=5,
        max_length=200,
    )

    description: str = Field(
        min_length=10,
        max_length=5000,
    )
