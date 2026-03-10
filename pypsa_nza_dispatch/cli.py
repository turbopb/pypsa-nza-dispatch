#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
cli.py

Description:
    Command-line interface for the PyPSA-NZA dispatch validation package.

    Provides a user-friendly CLI for running stress tests and single scenario
    validations with configurable parameters.

Background:
    After download from the GitHub reoo, there should br several modules in the 
    pypsa_nza_dispatch directory, i.e.
    
    Mode                 LastWriteTime         Length Name
    ----                 -------------         ------ ----
    d-----        26/02/2026   1:11 pm                __pycache__
    -a----        26/02/2026   1:07 pm           6757 cli.py
    -a----        26/02/2026  12:00 pm           7547 diagnostics.py
    -a----        26/02/2026  11:39 am           7085 network.py
    -a----        12/02/2026   7:27 pm           4074 utils.py
    -a----        26/02/2026  12:27 pm           7640 validate.py
    -a----        12/02/2026   7:27 pm            990 __init__.py

    Module 'cli.py' is the top level orchestrater that directs the execution of 
    appropriate functionality from the modules (diagnostics.py, network.py, utils.py
    and validate.py) based on what is specified on the command line invocation.
    
    However, it should also be noted that 'cli.py' is executed indirectly via the     
    "nza-dispatch-validate" command which points to "cli.py" inside the pyproject.toml:
        
        .....
        [project.scripts]
        nza-dispatch-validate = "pypsa_nza_dispatch.cli:main"
        .....
    
    In simplistic terms this tells Python: "When someone types "nza-dispatch-validate", 
    run the main() function from pypsa_nza_dispatch/cli.py".

Workflow:        
    The following is a typical ommand line invocation and sequence:  
        
        nza-dispatch-validate --config config.yaml --year 2024 --month jan    
         ↓
        cli.py main()
             ↓
        1. Parse arguments
             ↓
        2. network.py → load_network()
             ↓
        3. validate.py → run_stress_test()
             ↓
        4. diagnostics.py → analyze_results()
             ↓
        5. Save CSV output
    
    How the Modules Work Together
    
    cli.py - 
    The orchestrator (entry point)
    Parses command-line arguments (--year, --month, --config, etc.)
    Calls functions from other modules in sequence
    Controls the overall workflow
    
    network.py - 
    Network loading and preparation
    Loads PyPSA network from CSV files
    Adds load shedding generators
    Prepares network for optimization
    
    validate.py - 
    Runs validation/stress testing
    Scales demand by MBIE factors
    Runs dispatch optimization (calls HiGHS solver)
    Collects results for different scaling factors
    
    diagnostics.py - 
    Analyzes results
    Calculates load shedding metrics
    Identifies transmission bottlenecks
    Determines if generation or transmission constrained
    
    utils.py - 
    Helper functions
    File I/O utilities
    Data processing helpers
    Common functions used by other modules
    
Type "nza-dispatch-validate --help" to get a listing of various command-line
options. (NOTE: you don't rutn 'python').

Author: Phillippe Bruneau
Modified: 2025-01
"""

import sys
import argparse
from pathlib import Path
import time
import pandas as pd

from pypsa_nza_dispatch import __version__
from pypsa_nza_dispatch.utils import load_config, validate_data_paths
from pypsa_nza_dispatch.network import (
    load_base_network,
    fix_all_capacities,
    add_load_shedding_generators,
    get_mbie_scaling_factors,
)
from pypsa_nza_dispatch.validate import run_stress_test, validate_single_scenario
from pypsa_nza_dispatch.diagnostics import generate_report


def create_parser():
    """Create and configure argument parser."""
    parser = argparse.ArgumentParser(
        prog='nza-dispatch-validate',
        description='PyPSA-NZA Dispatch Validation and Capacity Stress Testing',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run stress test for 2024 using April as representative month
  nza-dispatch-validate --year 2024 --month apr --config config/dispatch_config.yaml

  # Test specific demand growth percentage
  nza-dispatch-validate --year 2024 --month apr --growth 25.0

  # Use different solver
  nza-dispatch-validate --year 2024 --month apr --solver glpk

  # Test up to year 2040
  nza-dispatch-validate --year 2024 --month apr --max-year 2040
        """
    )

    parser.add_argument(
        '--version',
        action='version',
        version=f'%(prog)s {__version__}'
    )

    parser.add_argument(
        '--config',
        type=str,
        required=True,
        help='Path to configuration YAML file'
    )

    parser.add_argument(
        '--year',
        type=int,
        required=True,
        help='Base year for network (e.g., 2024, 2025)'
    )

    parser.add_argument(
        '--month',
        type=str,
        default='apr',
        help='Representative month (jan, feb, ..., dec). Default: apr'
    )

    parser.add_argument(
        '--scenario',
        type=str,
        default='reference',
        help='MBIE scenario name (reference, constraint, etc.). Default: reference'
    )

    parser.add_argument(
        '--max-year',
        type=int,
        default=2040,
        help='Maximum year for MBIE growth factors. Default: 2040'
    )

    parser.add_argument(
        '--growth',
        type=float,
        help='Test single demand growth percentage (e.g., 25.0 for +25%%)'
    )

    parser.add_argument(
        '--solver',
        type=str,
        default='highs',
        help='Optimization solver (highs, gurobi, glpk, etc.). Default: highs'
    )

    parser.add_argument(
        '--load-shed-cost',
        type=float,
        default=1e4,
        help='Load shedding marginal cost ($/MWh). Default: 10000'
    )

    parser.add_argument(
        '--output-dir',
        type=str,
        help='Output directory for results. Default: results/dispatch_validation/'
    )

    parser.add_argument(
        '--quiet',
        action='store_true',
        help='Suppress progress output'
    )

    return parser


def main():
    """Main CLI entry point."""
    parser = create_parser()
    args = parser.parse_args()

    verbose = not args.quiet

    if verbose:
        print("\n" + "#"*60)
        print("# PyPSA-NZA DISPATCH VALIDATION")
        print(f"# Version {__version__}")
        print("#"*60)

    start_time = time.time()

    # Load configuration
    try:
        config = load_config(args.config)
        validate_data_paths(config)
    except Exception as e:
        print(f"\n Configuration error: {e}")
        return 1

    # Extract scenario from config if not overridden
    scenario = config.get('scenario', args.scenario)

    if verbose:
        print(f"\nConfiguration:")
        print(f"  Config file: {args.config}")
        print(f"  Data root: {config['paths']['root']}")
        print(f"  Year: {args.year}")
        print(f"  Month: {args.month}")
        print(f"  Scenario: {scenario}")
        print(f"  Solver: {args.solver}")

    # Load network
    try:
        network = load_base_network(config, args.year, args.month)
    except Exception as e:
        print(f"\n Failed to load network: {e}")
        return 1

    # Prepare network
    network = fix_all_capacities(network, verbose=verbose)
    network = add_load_shedding_generators(
        network,
        marginal_cost=args.load_shed_cost,
        verbose=verbose
    )

    # Determine output directory
    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        # Use path relative to data root
        output_dir = Path(config['paths']['root']) / 'results' / 'dispatch_validation'

    output_dir.mkdir(parents=True, exist_ok=True)

    # Run validation
    if args.growth is not None:
        # Single scenario test
        scaling_factor = 1.0 + (args.growth / 100.0)
        diagnostics = validate_single_scenario(
            network,
            scaling_factor=scaling_factor,
            solver_name=args.solver,
            verbose=verbose
        )

        # Save single result
        output_path = output_dir / f"validation_{args.year}_{args.month}_growth{args.growth:.1f}.csv"
        result_df = pd.DataFrame([{
            'scaling_factor': scaling_factor,
            'growth_percent': args.growth,
            **diagnostics
        }])
        result_df.to_csv(output_path, index=False)
        if verbose:
            print(f"\n✓ Results saved to: {output_path}")

    else:
        # Full stress test with MBIE growth factors
        try:
            scaling_factors = get_mbie_scaling_factors(
                config,
                scenario,
                args.year,
                args.max_year
            )
        except Exception as e:
            print(f"\n Failed to get MBIE scaling factors: {e}")
            return 1

        if verbose:
            print(f"\n  MBIE scaling factors: {len(scaling_factors)}")
            print(f"  Range: {scaling_factors[0]:.4f} to {scaling_factors[-1]:.4f}")

        # Run stress test
        results = run_stress_test(
            network,
            scaling_factors,
            solver_name=args.solver,
            verbose=verbose
        )

        # Generate report
        output_path = output_dir / f"stress_test_{scenario}_{args.year}_{args.month}.csv"
        generate_report(results, output_path, verbose=verbose)

    # Summary
    elapsed = time.time() - start_time
    if verbose:
        print(f"\n{'='*60}")
        print(f" Validation complete")
        print(f"  Time: {elapsed:.1f}s ({elapsed/60:.1f} min)")
        print(f"{'='*60}\n")

    return 0


if __name__ == '__main__':
    sys.exit(main())
