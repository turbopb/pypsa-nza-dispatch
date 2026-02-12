"""
PyPSA-NZA Dispatch Validation
==============================

Capacity adequacy stress testing and dispatch validation for PyPSA-NZ networks.

Main modules:
- validate: Core validation and stress testing logic
- network: Network loading and preparation
- diagnostics: Metrics calculation and bottleneck analysis
- utils: Utility functions
"""

__version__ = "0.1.0"
__author__ = "Phillippe Bruneau"

from pypsa_nza_dispatch.validate import run_stress_test, run_dispatch
from pypsa_nza_dispatch.network import (
    load_base_network,
    fix_all_capacities,
    add_load_shedding_generators,
    scale_demand,
)
from pypsa_nza_dispatch.diagnostics import (
    calculate_diagnostics,
    diagnose_bottleneck_type,
    generate_report,
)

__all__ = [
    "run_stress_test",
    "run_dispatch",
    "load_base_network",
    "fix_all_capacities",
    "add_load_shedding_generators",
    "scale_demand",
    "calculate_diagnostics",
    "diagnose_bottleneck_type",
    "generate_report",
]
