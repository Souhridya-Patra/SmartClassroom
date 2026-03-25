from pydantic import BaseModel, EmailStr

class ProfessorBase(BaseModel):
    name: str
    email: EmailStr

class ProfessorCreate(ProfessorBase):
    pass

class Professor(ProfessorBase):
    id: int

    class Config:
        orm_mode = True
