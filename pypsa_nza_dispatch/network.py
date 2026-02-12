"""
Network loading and preparation functions for dispatch validation.

Handles loading PyPSA networks, fixing capacities, adding load shedding
generators, and scaling demand.
"""

from pathlib import Path
from typing import Dict
import pypsa
from pypsa_nza_dispatch.utils import get_network_path, print_heading


def load_base_network(config: Dict, year: int, month: str) -> pypsa.Network:
    """
    Load a customized network from disk.

    This loads a network that has already been processed by both
    nza_cx_net.py and nza_cx_customize.py (with profiles and costs).

    Parameters
    ----------
    config : dict
        Configuration dictionary with paths
    year : int
        Network year
    month : str
        Month abbreviation (e.g., 'jan', 'apr')

    Returns
    -------
    pypsa.Network
        Loaded network with all customizations

    Raises
    ------
    FileNotFoundError
        If network directory not found
    """
    network_path = get_network_path(config, year, month)

    if not network_path.exists():
        raise FileNotFoundError(f"Network not found: {network_path}")

    print_heading(f"LOADING BASE NETWORK: {month}_{year}", char='=')

    n = pypsa.Network()
    n.import_from_csv_folder(str(network_path))

    print(f"  Buses: {len(n.buses)}")
    print(f"  Lines: {len(n.lines)}")
    print(f"  Links: {len(n.links)}")
    print(f"  Generators: {len(n.generators)}")
    print(f"  Loads: {len(n.loads)}")
    print(f"  Snapshots: {len(n.snapshots)}")

    return n


def fix_all_capacities(network: pypsa.Network, verbose: bool = True) -> pypsa.Network:
    """
    Fix all generation and transmission capacities (disable expansion).

    Sets all extendable flags to False so optimizer cannot add capacity.
    This creates a dispatch-only problem with fixed infrastructure.

    Parameters
    ----------
    network : pypsa.Network
        Network to modify (modified in place)
    verbose : bool
        Whether to print details

    Returns
    -------
    pypsa.Network
        Network with all capacities fixed
    """
    if verbose:
        print_heading("FIXING CAPACITIES (DISABLING EXPANSION)", char='=')

    # Fix generators
    if 'p_nom_extendable' in network.generators.columns:
        extendable_count = network.generators['p_nom_extendable'].sum()
        network.generators['p_nom_extendable'] = False
        if verbose:
            print(f"  ✓ Fixed {extendable_count} extendable generators")

    # Fix storage units (if present)
    if len(network.storage_units) > 0 and 'p_nom_extendable' in network.storage_units.columns:
        extendable_count = network.storage_units['p_nom_extendable'].sum()
        network.storage_units['p_nom_extendable'] = False
        if verbose:
            print(f"  ✓ Fixed {extendable_count} extendable storage units")

    # Fix transmission lines
    if 's_nom_extendable' in network.lines.columns:
        extendable_count = network.lines['s_nom_extendable'].sum()
        network.lines['s_nom_extendable'] = False
        if verbose:
            print(f"  ✓ Fixed {extendable_count} extendable lines")

    # Fix HVDC links
    if len(network.links) > 0 and 'p_nom_extendable' in network.links.columns:
        extendable_count = network.links['p_nom_extendable'].sum()
        network.links['p_nom_extendable'] = False
        if verbose:
            print(f"  ✓ Fixed {extendable_count} extendable links")

    return network


def add_load_shedding_generators(
    network: pypsa.Network,
    marginal_cost: float = 1e4,
    verbose: bool = True
) -> pypsa.Network:
    """
    Add load shedding generators at each load bus.

    These generators have very high marginal cost and unlimited capacity.
    Any dispatch of these generators indicates system inadequacy.

    Spatially distributed shedding helps identify WHERE failures occur,
    which is critical for diagnosing transmission vs generation bottlenecks.

    Parameters
    ----------
    network : pypsa.Network
        Network to modify (modified in place)
    marginal_cost : float
        Very high cost to discourage use (default: 10,000 $/MWh)
    verbose : bool
        Whether to print details

    Returns
    -------
    pypsa.Network
        Network with load shedding generators added
    """
    if verbose:
        print_heading("ADDING LOAD SHEDDING GENERATORS", char='=')

    # Get all buses with loads
    load_buses = network.loads['bus'].unique()

    for bus in load_buses:
        network.add(
            "Generator",
            f"load_shed_{bus}",
            bus=bus,
            p_nom=1e6,  # Essentially unlimited (1000 GW)
            marginal_cost=marginal_cost,
            carrier="load_shedding",
            p_min_pu=0.0,
            p_max_pu=1.0
        )

    if verbose:
        print(f"  ✓ Added {len(load_buses)} load shedding generators")
        print(f"  Marginal cost: ${marginal_cost:,.0f}/MWh")

    return network


def scale_demand(network: pypsa.Network, scaling_factor: float) -> pypsa.Network:
    """
    Scale all load demands by a constant factor.

    Parameters
    ----------
    network : pypsa.Network
        Network to modify (modified in place)
    scaling_factor : float
        Multiplicative scaling factor (e.g., 1.2 = 20% increase)

    Returns
    -------
    pypsa.Network
        Network with scaled loads
    """
    # Scale time-varying loads
    network.loads_t.p_set *= scaling_factor

    # Also scale fixed loads if present (though typically loads are time-varying)
    if 'p_set' in network.loads.columns:
        network.loads['p_set'] *= scaling_factor

    return network


def get_mbie_scaling_factors(
    config: Dict,
    scenario: str,
    base_year: int,
    max_year: int = None
) -> list:
    """
    Extract MBIE demand growth scaling factors from config.

    Parameters
    ----------
    config : dict
        Configuration dictionary
    scenario : str
        Scenario name (e.g., 'reference')
    base_year : int
        Base year (scaling = 1.0)
    max_year : int, optional
        Maximum year to include

    Returns
    -------
    list of float
        Scaling factors sorted by value

    Raises
    ------
    ValueError
        If scenario not found in config
    """
    if 'demand_scenarios' not in config:
        raise ValueError("Configuration missing 'demand_scenarios' section")

    if scenario not in config['demand_scenarios']:
        raise ValueError(f"Scenario '{scenario}' not found in configuration")

    growth_factors = config['demand_scenarios'][scenario]

    # Filter years
    factors = []
    for year, factor in sorted(growth_factors.items()):
        if year >= base_year:
            if max_year is None or year <= max_year:
                factors.append(factor)

    return sorted(set(factors))  # Remove duplicates and sort
