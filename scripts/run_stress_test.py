#!/usr/bin/env python
"""
Example: Running a dispatch validation stress test

This script demonstrates how to use the pypsa_nza_dispatch package
to run a capacity adequacy stress test.
"""

from pathlib import Path
from pypsa_nza_dispatch import (
    load_base_network,
    fix_all_capacities,
    add_load_shedding_generators,
    run_stress_test,
    generate_report,
)
from pypsa_nza_dispatch.utils import load_config
from pypsa_nza_dispatch.network import get_mbie_scaling_factors


def main():
    """Run example stress test."""
    
    # Configuration
    config_file = 'config/dispatch_config.yaml'
    year = 2024
    month = 'apr'  # Representative month
    scenario = 'reference'
    max_year = 2040
    solver = 'highs'
    
    print("="*60)
    print("PyPSA-NZA Dispatch Validation - Example")
    print("="*60)
    
    # Load configuration
    print("\n1. Loading configuration...")
    config = load_config(config_file)
    print(f"   Data root: {config['paths']['root']}")
    
    # Load network
    print(f"\n2. Loading network ({year}, {month})...")
    network = load_base_network(config, year, month)
    
    # Prepare for dispatch validation
    print("\n3. Preparing network for dispatch validation...")
    network = fix_all_capacities(network, verbose=True)
    network = add_load_shedding_generators(network, marginal_cost=1e4, verbose=True)
    
    # Get MBIE scaling factors
    print(f"\n4. Getting MBIE scaling factors ({scenario}, up to {max_year})...")
    scaling_factors = get_mbie_scaling_factors(config, scenario, year, max_year)
    print(f"   Number of scenarios: {len(scaling_factors)}")
    print(f"   Range: {scaling_factors[0]:.4f} to {scaling_factors[-1]:.4f}")
    
    # Run stress test
    print(f"\n5. Running stress test with {solver} solver...")
    results = run_stress_test(
        network,
        scaling_factors,
        solver_name=solver,
        verbose=True
    )
    
    # Generate report
    print("\n6. Generating report...")
    output_dir = Path(config['paths']['root']) / 'results' / 'dispatch_validation'
    output_path = output_dir / f"example_stress_test_{year}_{month}.csv"
    generate_report(results, output_path, verbose=True)
    
    print("\n" + "="*60)
    print("Example complete!")
    print("="*60)
    
    return results


if __name__ == '__main__':
    results = main()
    
    # Optional: Additional analysis
    print("\nQuick analysis of results:")
    adequate = results[results['status'] == 'ADEQUATE']
    inadequate = results[results['status'] == 'INADEQUATE']
    
    if len(adequate) > 0:
        print(f"\nSystem adequate up to {adequate['growth_percent'].max():.1f}% demand growth")
    
    if len(inadequate) > 0:
        first_failure = inadequate.iloc[0]
        print(f"First failure at {first_failure['growth_percent']:.1f}% growth")
        print(f"  Load shed: {first_failure['load_shed_MWh']:.0f} MWh "
              f"({first_failure['load_shed_fraction']*100:.2f}%)")
