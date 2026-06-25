"""Abstract model interface so models are swappable in the pipeline."""
from __future__ import annotations
from abc import ABC, abstractmethod
import numpy as np
import pandas as pd

class BaseModel(ABC):
    @abstractmethod
    def fit(self, history: pd.DataFrame) -> None: ...

    @abstractmethod
    def score_matrix(self, home: str, away: str) -> np.ndarray:
        """Return normalized P(home i, away j) matrix."""
