from abc import ABC, abstractmethod

class IndicatorBase(ABC):
    @abstractmethod
    def update(self, price: float) -> None:
        pass

    @abstractmethod
    def get_trend(self) -> str:
        """Return one of: 'up', 'down', 'sideways'"""
        pass
