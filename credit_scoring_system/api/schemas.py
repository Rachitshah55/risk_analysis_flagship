from typing import Any, Dict, List
from pydantic import BaseModel, RootModel, Field

# Single record as a free-form dict, wrapped as a RootModel
class CreditRecord(RootModel[Dict[str, Any]]):
    def as_dict(self) -> Dict[str, Any]:
        # pydantic v2 root access
        return self.root

# Batch payload: list of free-form dicts
class CreditBatch(BaseModel):
    records: List[Dict[str, Any]] = Field(default_factory=list)
