from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol

@dataclass(slots=True)
class NormalizedRecord:
    source: str
    external_id: str
    text: str = ""
    author: str | None = None
    url: str | None = None
    published_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

class Connector(Protocol):
    name: str
    async def search(self, query: str, limit: int = 50) -> list[NormalizedRecord]: ...

class ConnectorRegistry:
    def __init__(self) -> None:
        self._connectors: dict[str, Connector] = {}
    def register(self, connector: Connector) -> None:
        if connector.name in self._connectors:
            raise ValueError(f"connector already registered: {connector.name}")
        self._connectors[connector.name] = connector
    def get(self, name: str) -> Connector:
        try: return self._connectors[name]
        except KeyError as exc: raise KeyError(f"unknown connector: {name}") from exc
    def names(self) -> tuple[str, ...]: return tuple(sorted(self._connectors))
