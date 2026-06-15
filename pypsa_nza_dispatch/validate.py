"""
Core validation and stress testing functions.
Contains the main workflow for running dispatch optimization and
progressive demand scaling tests.
"""
import time
from typing import Tuple, Dict, List
import pandas as pd
import pypsa
from pypsa_nza_dispatch.network import scale_demand
from pypsa_nza_dispatch.diagnostics import (
    calculate_diagnostics,
    print_diagnostics_summary
)
from pypsa_nza_dispatch.utils import print_heading


def run_dispatch(
    network: pypsa.Network,
    solver_name: str = 'highs',
    solver_options: Dict = None
) -> Tuple[bool, Dict]:
    """
    Run optimal dispatch with fixed capacities.

    Uses transport model (x_pu_eff=0) to allow cross-island power flow
    through HVDC links without KVL angle constraints blocking transfer.
    This is standard practice for capacity planning models with HVDC.
    """
    if solver_options is None:
        solver_options = {'log_to_console': False}

    try:
        # Switch to transport model: zero line reactances so KVL does not
        # block power flow across HVDC links between AC sub-networks.
        # This is correct for capacity planning -- we are checking whether
        # sufficient generation exists, not solving AC power flow angles.
        network.lines['x_pu_eff'] = 0.0
        network.lines['x_pu']     = 0.0

        status = network.optimize(
            solver_name=solver_name,
            solver_options=solver_options
        )

        success = False
        if isinstance(status, str):
            success = (status == 'ok')
        elif isinstance(status, tuple):
            success = (status[0] == 'ok')
        elif hasattr(status, 'status'):
            success = (status.status == 'ok')
        else:
            success = hasattr(network, 'objective') and network.objective is not None

        diagnostics = calculate_diagnostics(network)
        return (success, diagnostics)

    except Exception as e:
        print(f"   Optimization failed: {e}")
        return (False, {})


def run_stress_test(
    base_network: pypsa.Network,
    scaling_factors: List[float],
    solver_name: str = 'highs',
    solver_options: Dict = None,
    stop_on_massive_failure: bool = True,
    massive_failure_threshold: float = 0.5,
) -> pd.DataFrame:
    """
    Run progressive demand scaling stress test.
    """
    if solver_options is None:
        solver_options = {'log_to_console': False}

    results = []

    print_heading("STRESS TEST", char='=')
    print(f"Testing {len(scaling_factors)} scaling factors")

    for i, factor in enumerate(scaling_factors):
        print(f"\n  [{i+1}/{len(scaling_factors)}] Scaling factor: {factor:.4f} "
              f"(+{(factor-1)*100:.1f}%)")

        test_network = base_network.copy()
        test_network = scale_demand(test_network, factor)

        success, diagnostics = run_dispatch(test_network, solver_name, solver_options)

        result = {
            'scaling_factor': factor,
            'growth_percent': (factor - 1) * 100,
            'status': diagnostics.get('status', 'FAILED'),
            'load_shed_MWh': diagnostics.get('total_load_shed_MWh', 0),
            'load_shed_fraction': diagnostics.get('load_shed_fraction', 0),
            'max_line_loading': diagnostics.get('max_line_loading', 0),
            'congested_lines': diagnostics.get('congested_lines', 0),
            'generators_at_capacity': diagnostics.get('generators_at_capacity', 0),
            'buses_with_shedding': diagnostics.get('buses_with_shedding', 0),
        }
        results.append(result)
        print_diagnostics_summary(diagnostics, factor)

        if (stop_on_massive_failure and
                diagnostics.get('load_shed_fraction', 0) > massive_failure_threshold):
            print(f"\n  Stopping: massive failure at factor {factor:.4f}")
            break

    return pd.DataFrame(results)


def validate_single_scenario(
    network: pypsa.Network,
    solver_name: str = 'highs',
    solver_options: Dict = None,
    scaling_factor: float = 1.0,
    **kwargs,
) -> Dict:
    """
    Validate a single network scenario.
    Returns diagnostics dict.
    """
    if solver_options is None:
        solver_options = {'log_to_console': False}

    if scaling_factor != 1.0:
        network = scale_demand(network, scaling_factor)

    success, diagnostics = run_dispatch(network, solver_name, solver_options)
    return diagnostics
