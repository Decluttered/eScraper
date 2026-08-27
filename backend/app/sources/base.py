"""Source adapter base module.

Every marketplace or import adapter implements the SourceAdapter protocol
defined in app.schemas.sources. Adapters convert source-specific records into
the source-neutral SourceEnvelope without performing any market or financial
calculations.
"""

from app.schemas.sources import SourceAdapter, SourceEnvelope, SourceHealth

__all__ = ["SourceAdapter", "SourceEnvelope", "SourceHealth"]
