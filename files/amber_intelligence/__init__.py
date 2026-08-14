"""Case intelligence services for the AMBER ICI.

The package is intentionally standard-library only and extends AMBER's existing
launcher and storage model.
"""

from .service import CaseIntelligence, IntelligenceError
from .templates import investigation_role_templates

__all__ = ["CaseIntelligence", "IntelligenceError", "investigation_role_templates"]
