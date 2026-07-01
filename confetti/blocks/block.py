from __future__ import annotations

from abc import ABC, abstractmethod


class Block(ABC):
    @abstractmethod
    def to_markdown(self) -> str: ...

    @abstractmethod
    def to_xhtml(self) -> str: ...
