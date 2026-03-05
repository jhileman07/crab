from abc import ABC, abstractmethod
from typing import Generic, TypeVar

T = TypeVar("T")


class BaseRunner(ABC, Generic[T]):
    @abstractmethod
    def run(self) -> T:
        pass
