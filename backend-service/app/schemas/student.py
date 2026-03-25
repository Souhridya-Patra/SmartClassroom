from pydantic import BaseModel, EmailStr

class StudentBase(BaseModel):
    id: str
    name: str
    email: EmailStr

class StudentCreate(StudentBase):
    pass

class Student(StudentBase):
    model_config = {"from_attributes": True}
