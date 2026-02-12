"""
Diagnostic functions for dispatch validation analysis.

Calculates performance metrics, identifies bottlenecks, and generates reports.
"""

from typing import Dict
from pathlib import Path
import pandas as pd
import pypsa
from pypsa_nza_dispatch.utils import print_heading, format_mwh


def calculate_diagnostics(network: pypsa.Network) -> Dict:
    """
    Calculate comprehensive dispatch diagnostics.

    Parameters
    ----------
    network : pypsa.Network
        Optimized network

    Returns
    -------
    dict
        Diagnostic metrics including:
        - Load shedding (total and by bus)
        - Line and link loading
        - Generator capacity utilization
        - System adequacy status
    """
    diagnostics = {}

    # Load shedding analysis
    load_shed_gens = [g for g in network.generators.index if g.startswith('load_shed_')]

    if len(load_shed_gens) > 0:
        total_load_shed = network.generators_t.p[load_shed_gens].sum().sum()
        diagnostics['total_load_shed_MWh'] = total_load_shed

        # Shedding by bus
        shed_by_bus = network.generators_t.p[load_shed_gens].sum()
        diagnostics['buses_with_shedding'] = (shed_by_bus > 0.01).sum()
        diagnostics['shedding_by_bus'] = shed_by_bus[shed_by_bus > 0.01].to_dict()
    else:
        diagnostics['total_load_shed_MWh'] = 0
        diagnostics['buses_with_shedding'] = 0

    # Total demand
    total_demand = network.loads_t.p_set.sum().sum()
    diagnostics['total_demand_MWh'] = total_demand
    diagnostics['load_shed_fraction'] = (
        diagnostics['total_load_shed_MWh'] / total_demand if total_demand > 0 else 0
    )

    # Generation dispatch
    gen_dispatch = network.generators_t.p.sum()
    diagnostics['total_generation_MWh'] = gen_dispatch.sum()

    # Line loading analysis
    line_loading = network.lines_t.p0.abs().max() / network.lines.s_nom
    diagnostics['max_line_loading'] = line_loading.max()
    diagnostics['congested_lines'] = (line_loading > 0.95).sum()
    diagnostics['lines_at_limit'] = line_loading[line_loading > 0.95].to_dict()

    # Link loading (HVDC)
    if len(network.links) > 0:
        link_loading = network.links_t.p0.abs().max() / network.links.p_nom
        diagnostics['max_link_loading'] = link_loading.max()
        diagnostics['congested_links'] = (link_loading > 0.95).sum()
    else:
        diagnostics['max_link_loading'] = 0
        diagnostics['congested_links'] = 0

    # Generator capacity utilization
    non_shed_gens = [g for g in network.generators.index if not g.startswith('load_shed_')]
    if len(non_shed_gens) > 0:
        gen_capacity_usage = (
            network.generators_t.p[non_shed_gens].max() / 
            network.generators.loc[non_shed_gens, 'p_nom']
        )
        diagnostics['generators_at_capacity'] = (gen_capacity_usage > 0.95).sum()
    else:
        diagnostics['generators_at_capacity'] = 0

    # System adequacy status
    if diagnostics['total_load_shed_MWh'] > 0.01:
        diagnostics['status'] = 'INADEQUATE'
    else:
        diagnostics['status'] = 'ADEQUATE'

    return diagnostics


def diagnose_bottleneck_type(diagnostics: Dict) -> str:
    """
    Determine primary bottleneck type from diagnostics.

    Analyzes patterns in load shedding, transmission congestion, and
    generation constraints to identify the limiting factor.

    Parameters
    ----------
    diagnostics : dict
        Diagnostic metrics from calculate_diagnostics

    Returns
    -------
    str
        Bottleneck diagnosis description
    """
    if diagnostics['status'] == 'ADEQUATE':
        return "System adequate - no bottleneck"

    # Check transmission bottleneck indicators
    transmission_constrained = (
        diagnostics.get('congested_lines', 0) > 0 or
        diagnostics.get('congested_links', 0) > 0
    )

    # Check generation bottleneck indicators
    generation_constrained = diagnostics.get('generators_at_capacity', 0) > 5

    # Spatial pattern
    widespread_shedding = diagnostics.get('buses_with_shedding', 0) > 5

    if transmission_constrained and not generation_constrained:
        return "TRANSMISSION bottleneck - lines/links congested, spare generation exists"
    elif generation_constrained and widespread_shedding:
        return "GENERATION bottleneck - insufficient total capacity"
    elif transmission_constrained and generation_constrained:
        return "MIXED bottleneck - both transmission and generation constraints"
    else:
        return "UNCERTAIN - manual review of detailed results recommended"


def generate_report(
    results_df: pd.DataFrame,
    output_path: Path = None,
    verbose: bool = True
) -> pd.DataFrame:
    """
    Generate comprehensive stress test report.

    Parameters
    ----------
    results_df : pd.DataFrame
        Stress test results with columns:
        - scaling_factor
        - growth_percent
        - status
        - load_shed_MWh
        - etc.
    output_path : Path, optional
        Where to save report CSV
    verbose : bool
        Whether to print report to console

    Returns
    -------
    pd.DataFrame
        Same as input (for chaining)
    """
    if verbose:
        print_heading("STRESS TEST REPORT", char='=')

        # Summary statistics
        adequate_runs = results_df[results_df['status'] == 'ADEQUATE']
        inadequate_runs = results_df[results_df['status'] == 'INADEQUATE']

        print(f"\nRuns: {len(results_df)}")
        print(f"  Adequate: {len(adequate_runs)}")
        print(f"  Inadequate: {len(inadequate_runs)}")

        if len(adequate_runs) > 0:
            max_adequate_scaling = adequate_runs['scaling_factor'].max()
            max_adequate_growth = adequate_runs['growth_percent'].max()
            print(f"\nMaximum adequate scaling:")
            print(f"  Factor: {max_adequate_scaling:.4f}")
            print(f"  Growth: +{max_adequate_growth:.1f}%")

        if len(inadequate_runs) > 0:
            first_failure = inadequate_runs.iloc[0]
            print(f"\nFirst failure:")
            print(f"  Scaling: {first_failure['scaling_factor']:.4f} "
                  f"(+{first_failure['growth_percent']:.1f}%)")
            print(f"  Load shed: {format_mwh(first_failure['load_shed_MWh'])} "
                  f"({first_failure['load_shed_fraction']*100:.2f}%)")

    # Save to CSV
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        results_df.to_csv(output_path, index=False)
        if verbose:
            print(f"\n✓ Results saved to: {output_path}")

    return results_df


def print_diagnostics_summary(diagnostics: Dict, scaling_factor: float) -> None:
    """
    Print a concise summary of diagnostics for a single run.

    Parameters
    ----------
    diagnostics : dict
        Diagnostic metrics
    scaling_factor : float
        Demand scaling factor for this run
    """
    growth_pct = (scaling_factor - 1) * 100

    if diagnostics['status'] == 'ADEQUATE':
        print(f"    ✓ ADEQUATE - no load shedding")
    else:
        load_shed = diagnostics['total_load_shed_MWh']
        shed_frac = diagnostics['load_shed_fraction']
        print(f"    ✗ INADEQUATE - {format_mwh(load_shed)} shed ({shed_frac*100:.2f}%)")
        print(f"      Buses with shedding: {diagnostics['buses_with_shedding']}")
        print(f"      Max line loading: {diagnostics['max_line_loading']*100:.1f}%")

        # Print bottleneck diagnosis
        diagnosis = diagnose_bottleneck_type(diagnostics)
        print(f"      Diagnosis: {diagnosis}")
