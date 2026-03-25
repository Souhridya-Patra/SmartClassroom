from pydantic import BaseModel

class DeviceBase(BaseModel):
    name: str
    location: str = None

class DeviceCreate(DeviceBase):
    pass

class Device(DeviceBase):
    id: int

    class Config:
        orm_mode = True
