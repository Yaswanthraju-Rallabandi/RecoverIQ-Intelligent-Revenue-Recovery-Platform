from abc import ABC, abstractmethod
from typing import List, Dict, Any
from sqlalchemy.orm import Session

class BaseOpportunityDetector(ABC):
    @abstractmethod
    def detect(self, db: Session, merchant_id: str) -> List[Dict[str, Any]]:
        """
        Scans raw merchant entities and emits standard unified opportunity dictionaries.
        """
        pass