"""ODL (Ontology Definition Language) core module."""

from .loader import ODLLoader
from .validator import ODLValidator
from .normalizer import ODLNormalizer
from .ir import ODLIR
from .core import ODLProcessor
from .diff import ODLDiffEngine, DiffResult, Change, ChangeType, ChangeCategory

__all__ = [
    "ODLLoader",
    "ODLValidator",
    "ODLNormalizer",
    "ODLIR",
    "ODLProcessor",
    "ODLDiffEngine",
    "DiffResult",
    "Change",
    "ChangeType",
    "ChangeCategory",
]
