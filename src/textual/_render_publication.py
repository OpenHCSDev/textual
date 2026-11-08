"""Widget-owned source information carried by actual output cells."""

from __future__ import annotations

from abc import ABC, abstractmethod

from textual.geometry import Region


class RenderPublication:
    """Most widgets have no source work to commit when their cells are accepted."""

    def admit(self, region: Region) -> None:
        """Accept this exact screen rectangle from the captured render."""

    def retain(self, region: Region, sources: list[tuple[RenderPublication, Region]]) -> None:
        """No source information for ordinary widget paint."""


class SourcePublication(RenderPublication, ABC):
    """A render carrying source information that must follow writer admission."""

    def retain(self, region: Region, sources: list[tuple[RenderPublication, Region]]) -> None:
        sources.append((self, region))

    @abstractmethod
    def admit(self, region: Region) -> None:
        """Commit this source for the cells accepted by output."""


NO_RENDER_PUBLICATION = RenderPublication()
