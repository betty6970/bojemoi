from pydantic import BaseModel

class VMConfig(BaseModel):
    name: str
    vcpus: int
    memory_gb: int

