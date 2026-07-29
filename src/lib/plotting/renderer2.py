from abc import ABC, abstractmethod


class Renderer2(ABC):
    @abstractmethod
    def update(self): ...
