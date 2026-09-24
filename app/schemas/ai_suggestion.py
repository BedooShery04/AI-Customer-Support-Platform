from pydantic import BaseModel



class AISuggestionContent(BaseModel):
    """
    The structure expected from the AI when generating
    a support response suggestion.
    """

    suggestion: str