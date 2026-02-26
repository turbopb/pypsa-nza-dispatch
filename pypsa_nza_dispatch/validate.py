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

    Parameters
    ----------
    network : pypsa.Network
        Network with fixed capacities and load shedding generators
    solver_name : str
        Solver to use (default: 'highs')
    solver_options : dict, optional
        Additional solver options

    Returns
    -------
    success : bool
        Whether optimization succeeded
    diagnostics : dict
        Diagnostic metrics
    """
    if solver_options is None:
        solver_options = {'log_to_console': False}

    try:
        # Run optimization
        status = network.optimize(
            solver_name=solver_name,
            solver_options=solver_options
        )

        # Check if optimization succeeded
        # PyPSA can return different status formats
        success = False
        if isinstance(status, str):
            success = (status == 'ok')
        elif isinstance(status, tuple):
            success = (status[0] == 'ok')
        elif hasattr(status, 'status'):
            success = (status.status == 'ok')
        else:
            # If we can't determine status, check if network has results
            success = hasattr(network, 'objective') and network.objective is not None

        # Calculate diagnostics
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
    verbose: bool = True,
    stop_on_massive_failure: bool = True,
    massive_failure_threshold: float = 0.5
) -> pd.DataFrame:
    """
    Run progressive demand scaling stress test.

    Tests network adequacy at increasing demand levels by:
    1. Copying the base network
    2. Scaling demand by each factor
    3. Running dispatch optimization
    4. Recording diagnostics

    Parameters
    ----------
    base_network : pypsa.Network
        Base network with fixed capacities and load shedding
    scaling_factors : list of float
        Demand scaling factors to test (e.g., [1.0, 1.1, 1.2, ...])
    solver_name : str
        Solver to use (default: 'highs')
    solver_options : dict, optional
        Additional solver options
    verbose : bool
        Whether to print progress
    stop_on_massive_failure : bool
        Whether to stop testing if load shedding exceeds threshold
    massive_failure_threshold : float
        Fraction of demand shed to trigger early stopping (default: 0.5)

    Returns
    -------
    pd.DataFrame
        Results for each scaling factor with columns:
        - scaling_factor: Demand multiplier
        - growth_percent: % increase from base
        - status: ADEQUATE or INADEQUATE
        - total_demand_MWh: Total energy demand
        - load_shed_MWh: Energy not served
        - load_shed_fraction: Fraction of demand shed
        - buses_with_shedding: Number of buses with shedding
        - max_line_loading: Maximum line utilization
        - congested_lines: Number of congested lines
        - generators_at_capacity: Number of generators at capacity
        - solve_time_s: Optimization time
    """
    if verbose:
        print_heading("RUNNING STRESS TEST", char='=')
        print(f"  Scaling factors: {len(scaling_factors)}")
        print(f"  Range: {scaling_factors[0]:.2f} - {scaling_factors[-1]:.2f}")
        print(f"  Solver: {solver_name}")

    results_list = []

    for i, factor in enumerate(scaling_factors):
        if verbose:
            print(f"\n  [{i+1}/{len(scaling_factors)}] Testing scaling factor: "
                  f"{factor:.4f} (+{(factor-1)*100:.1f}%)")

        # Copy network and scale demand
        n = base_network.copy()
        n = scale_demand(n, factor)

        # Run dispatch
        start_time = time.time()
        success, diagnostics = run_dispatch(n, solver_name, solver_options)
        elapsed = time.time() - start_time

        if not success:
            if verbose:
                print(f"     Optimization failed")
            continue

        # Store results
        result = {
            'scaling_factor': factor,
            'growth_percent': (factor - 1) * 100,
            'status': diagnostics.get('status', 'UNKNOWN'),
            'total_demand_MWh': diagnostics.get('total_demand_MWh', 0),
            'load_shed_MWh': diagnostics.get('total_load_shed_MWh', 0),
            'load_shed_fraction': diagnostics.get('load_shed_fraction', 0),
            'buses_with_shedding': diagnostics.get('buses_with_shedding', 0),
            'max_line_loading': diagnostics.get('max_line_loading', 0),
            'congested_lines': diagnostics.get('congested_lines', 0),
            'generators_at_capacity': diagnostics.get('generators_at_capacity', 0),
            'solve_time_s': elapsed
        }
        results_list.append(result)

        # Print summary
        if verbose:
            print_diagnostics_summary(diagnostics, factor)

        # Stop if massive failure
        if (stop_on_massive_failure and 
            diagnostics['load_shed_fraction'] > massive_failure_threshold):
            if verbose:
                print(f"     Stopping test - system far beyond capacity")
            break

    return pd.DataFrame(results_list)


def validate_single_scenario(
    network: pypsa.Network,
    scaling_factor: float = 1.0,
    solver_name: str = 'highs',
    solver_options: Dict = None,
    verbose: bool = True
) -> Dict:
    """
    Validate a single demand scenario.

    Convenience function for testing a single scaling factor without
    running a full stress test.

    Parameters
    ----------
    network : pypsa.Network
        Network with fixed capacities and load shedding
    scaling_factor : float
        Demand scaling factor (default: 1.0)
    solver_name : str
        Solver to use (default: 'highs')
    solver_options : dict, optional
        Additional solver options
    verbose : bool
        Whether to print results

    Returns
    -------
    dict
        Diagnostic metrics
    """
    if verbose:
        print_heading(f"VALIDATING SCENARIO (scaling={scaling_factor:.4f})", char='=')

    # Scale demand
    network = scale_demand(network, scaling_factor)

    # Run dispatch
    start_time = time.time()
    success, diagnostics = run_dispatch(network, solver_name, solver_options)
    elapsed = time.time() - start_time

    if not success:
        print(" Optimization failed")
        return {}

    diagnostics['solve_time_s'] = elapsed

    if verbose:
        print(f"\nStatus: {diagnostics['status']}")
        print(f"Total demand: {diagnostics['total_demand_MWh']:,.0f} MWh")
        print(f"Load shed: {diagnostics['total_load_shed_MWh']:,.0f} MWh "
              f"({diagnostics['load_shed_fraction']*100:.2f}%)")
        print(f"Max line loading: {diagnostics['max_line_loading']*100:.1f}%")
        print(f"Solve time: {elapsed:.1f}s")

    return diagnostics
