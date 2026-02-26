from pydantic import BaseModel

class MessageRequest(BaseModel):
    text: str
    

class MessageResponse(BaseModel):
    risk_level: str
    score: int
    action: str