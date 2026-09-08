"""CNBI v1.0 candidate — conservative notebook 03 extraction.

Status and limitations: README.md and AUDIT_REPORT.md.
"""
__version__ = "1.0.0rc2"

from .core import cnbi
from .payoff import canonical_payoff_starts, individual_payoff
from .spectral import parallel_analysis
from .pareto import nondominated, postprocess_frontier

__all__ = [
    "cnbi", "canonical_payoff_starts", "individual_payoff",
    "parallel_analysis", "nondominated", "postprocess_frontier", "__version__",
]
