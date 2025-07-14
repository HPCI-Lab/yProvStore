from pydantic import BaseModel


class SuccessResponse(BaseModel):
    """
    Model for successful response.
    """
    message: str = "Success"
