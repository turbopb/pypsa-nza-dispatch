"""
Basic tests for pypsa_nza_dispatch package.

These are minimal tests to verify the package structure and basic functionality.
More comprehensive tests can be added as needed.
"""

import pytest
from pypsa_nza_dispatch import __version__


def test_version():
    """Test that version is defined."""
    assert __version__ is not None
    assert isinstance(__version__, str)


def test_imports():
    """Test that main functions can be imported."""
    from pypsa_nza_dispatch import (
        run_stress_test,
        run_dispatch,
        load_base_network,
        fix_all_capacities,
        add_load_shedding_generators,
        scale_demand,
        calculate_diagnostics,
        diagnose_bottleneck_type,
        generate_report,
    )
    
    # Verify functions are callable
    assert callable(run_stress_test)
    assert callable(run_dispatch)
    assert callable(load_base_network)
    assert callable(fix_all_capacities)
    assert callable(add_load_shedding_generators)
    assert callable(scale_demand)
    assert callable(calculate_diagnostics)
    assert callable(diagnose_bottleneck_type)
    assert callable(generate_report)


def test_config_loading():
    """Test configuration loading with minimal config."""
    from pypsa_nza_dispatch.utils import load_config
    import tempfile
    import yaml
    from pathlib import Path
    
    # Create minimal test config
    test_config = {
        'paths': {
            'root': '/tmp/test',
            'dirpath_static': 'data/static',
        },
        'base_year': 2024,
        'scenario': 'reference',
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(test_config, f)
        config_path = f.name
    
    try:
        config = load_config(config_path)
        assert config['base_year'] == 2024
        assert config['scenario'] == 'reference'
    finally:
        Path(config_path).unlink()


def test_scaling_factors_extraction():
    """Test MBIE scaling factor extraction."""
    from pypsa_nza_dispatch.network import get_mbie_scaling_factors
    
    test_config = {
        'demand_scenarios': {
            'reference': {
                2024: 1.0,
                2025: 1.027,
                2026: 1.045,
                2027: 1.075,
            }
        }
    }
    
    factors = get_mbie_scaling_factors(
        test_config,
        scenario='reference',
        base_year=2024,
        max_year=2026
    )
    
    assert len(factors) == 3
    assert 1.0 in factors
    assert 1.027 in factors
    assert 1.045 in factors
    assert 1.075 not in factors  # Filtered by max_year


def test_bottleneck_diagnosis():
    """Test bottleneck type diagnosis logic."""
    from pypsa_nza_dispatch.diagnostics import diagnose_bottleneck_type
    
    # Test adequate system
    diagnostics_adequate = {
        'status': 'ADEQUATE',
        'total_load_shed_MWh': 0,
    }
    diagnosis = diagnose_bottleneck_type(diagnostics_adequate)
    assert 'adequate' in diagnosis.lower()
    
    # Test transmission bottleneck
    diagnostics_transmission = {
        'status': 'INADEQUATE',
        'congested_lines': 5,
        'generators_at_capacity': 2,
        'buses_with_shedding': 2,
    }
    diagnosis = diagnose_bottleneck_type(diagnostics_transmission)
    assert 'transmission' in diagnosis.lower()
    
    # Test generation bottleneck
    diagnostics_generation = {
        'status': 'INADEQUATE',
        'congested_lines': 0,
        'generators_at_capacity': 10,
        'buses_with_shedding': 8,
    }
    diagnosis = diagnose_bottleneck_type(diagnostics_generation)
    assert 'generation' in diagnosis.lower()


def test_format_utilities():
    """Test utility formatting functions."""
    from pypsa_nza_dispatch.utils import format_mwh, format_mw
    
    # Test MWh formatting
    assert 'TWh' in format_mwh(2_000_000)
    assert 'GWh' in format_mwh(2_000)
    assert 'MWh' in format_mwh(500)
    
    # Test MW formatting
    assert 'GW' in format_mw(2_000)
    assert 'MW' in format_mw(500)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
