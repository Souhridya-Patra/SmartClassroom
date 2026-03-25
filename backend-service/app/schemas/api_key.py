from pydantic import BaseModel

class APIKey(BaseModel):
    api_key: str
