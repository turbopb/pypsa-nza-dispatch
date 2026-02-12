# PyPSA-NZA Dispatch Validation

Capacity adequacy stress testing and dispatch validation for PyPSA-NZ electricity networks.

## Overview

This tool validates New Zealand electricity network capacity by:
- Running optimal dispatch with fixed infrastructure (no capacity expansion)
- Progressively scaling demand using MBIE growth projections
- Identifying system failure points and bottleneck types
- Distinguishing between transmission and generation constraints

**Key Features:**
- ✅ Spatially distributed load shedding diagnostics
- ✅ Progressive demand stress testing
- ✅ Automatic bottleneck identification (transmission vs generation)
- ✅ Command-line interface with configurable parameters
- ✅ Integration with MBIE demand scenarios
- ✅ Multiple solver support (HiGHS, Gurobi, GLPK, etc.)

## Installation

### Prerequisites

- Python 3.9, 3.10, or 3.11
- Pre-built PyPSA networks (from `nza_cx_net.py` and `nza_cx_customize.py`)
- Optimization solver (HiGHS recommended - free and open source)

### Quick Install

1. **Clone the repository:**
```bash
git clone https://github.com/yourusername/pypsa-nza-dispatch-validation.git
cd pypsa-nza-dispatch-validation
```

2. **Install in editable mode:**
```bash
pip install -e .
```

This installs the package and creates the `nza-dispatch-validate` command.

3. **Install solver (if not already installed):**

For HiGHS (recommended):
```bash
pip install highspy
```

For Gurobi (requires license):
```bash
pip install gurobipy
```

### Development Install

For development with testing and code formatting tools:
```bash
pip install -e ".[dev]"
```

## Configuration

### 1. Update Config File

Edit `config/dispatch_config.yaml` and set your data directory:

```yaml
paths:
  # CRITICAL: Set this to your main analysis/data directory
  root: "C:/Users/Public/Documents/Thesis/analysis"  # Windows
  # root: "/home/pbrun/thesis/analysis"              # Linux
```

This should point to the directory containing:
- `cases/reference/{year}/{month}_{year}/` - Pre-built networks
- `data/processed/static/` - Network topology data
- `data/costs/` - Technology cost data
- `data/external/mbie/` - MBIE scenarios

### 2. Verify Network Files Exist

Required network structure:
```
{root}/cases/reference/2024/apr_2024/
    ├── buses.csv
    ├── generators.csv
    ├── lines.csv
    ├── links.csv
    ├── loads.csv
    ├── loads-p_set.csv
    └── ...
```

These networks must be **fully customized** (with renewable profiles and costs applied).

## Usage

### Command Line Interface

**Basic stress test:**
```bash
nza-dispatch-validate --year 2024 --month apr --config config/dispatch_config.yaml
```

**Test specific demand growth:**
```bash
nza-dispatch-validate --year 2024 --month apr --growth 25.0 --config config/dispatch_config.yaml
```

**Use different solver:**
```bash
nza-dispatch-validate --year 2024 --month apr --solver gurobi --config config/dispatch_config.yaml
```

**Test up to specific year:**
```bash
nza-dispatch-validate --year 2024 --month apr --max-year 2040 --config config/dispatch_config.yaml
```

**Full options:**
```bash
nza-dispatch-validate --help
```

### Python API

```python
from pypsa_nza_dispatch import (
    load_base_network,
    fix_all_capacities,
    add_load_shedding_generators,
    run_stress_test,
    generate_report,
)
from pypsa_nza_dispatch.utils import load_config
from pypsa_nza_dispatch.network import get_mbie_scaling_factors

# Load configuration
config = load_config('config/dispatch_config.yaml')

# Load and prepare network
network = load_base_network(config, year=2024, month='apr')
network = fix_all_capacities(network)
network = add_load_shedding_generators(network)

# Get MBIE scaling factors
scaling_factors = get_mbie_scaling_factors(
    config, 
    scenario='reference', 
    base_year=2024, 
    max_year=2040
)

# Run stress test
results = run_stress_test(network, scaling_factors, solver_name='highs')

# Generate report
generate_report(results, output_path='results/stress_test.csv')
```

## Understanding Results

### Output Files

Results are saved to `{root}/results/dispatch_validation/`:
- `stress_test_{scenario}_{year}_{month}.csv` - Full stress test results

### Result Columns

| Column | Description |
|--------|-------------|
| `scaling_factor` | Demand multiplier (1.0 = base year) |
| `growth_percent` | % increase from base year |
| `status` | ADEQUATE or INADEQUATE |
| `total_demand_MWh` | Total energy demand |
| `load_shed_MWh` | Energy not served |
| `load_shed_fraction` | Fraction of demand shed (0-1) |
| `buses_with_shedding` | Number of buses with shedding |
| `max_line_loading` | Maximum line utilization (0-1) |
| `congested_lines` | Number of lines >95% loaded |
| `generators_at_capacity` | Number of generators >95% utilized |
| `solve_time_s` | Optimization time in seconds |

### Interpreting Bottlenecks

**Transmission Bottleneck:**
- Localized load shedding (few buses)
- High line/link loading (>95%)
- Spare generation capacity exists
- **Action:** Transmission reinforcement needed

**Generation Bottleneck:**
- Widespread load shedding (many buses)
- Most generators at capacity
- Line loading moderate (<80%)
- **Action:** New generation capacity needed

**Mixed Bottleneck:**
- Both constraints binding
- **Action:** Both transmission and generation expansion needed

### Example Output

```
STRESS TEST REPORT
================================================================

Runs: 17
  Adequate: 12
  Inadequate: 5

Maximum adequate scaling:
  Factor: 1.2204
  Growth: +22.0%

First failure:
  Scaling: 1.2447 (+24.5%)
  Load shed: 1,234 MWh (1.2%)
```

**Interpretation:** Current infrastructure adequate up to +22% demand growth. First failures at ~2035 demand levels (reference scenario).

## Month Selection

The tool tests a single representative month to improve computation speed:

| Month | Characteristics | When to Use |
|-------|----------------|-------------|
| **April** | Moderate demand | General testing |
| **July/August** | Winter peak demand | Conservative capacity test |
| **January/February** | Summer low demand | Minimum adequacy check |

For comprehensive analysis, run multiple months and compare.

## Advanced Usage

### Custom Scaling Factors

Instead of MBIE scenarios, test custom growth patterns:

```python
# Test 0% to 50% growth in 5% increments
scaling_factors = [1.0 + (i * 0.05) for i in range(11)]
results = run_stress_test(network, scaling_factors)
```

### Multiple Months

```python
months = ['jan', 'apr', 'jul', 'oct']  # Seasonal representation

for month in months:
    network = load_base_network(config, 2024, month)
    network = fix_all_capacities(network)
    network = add_load_shedding_generators(network)
    
    results = run_stress_test(network, scaling_factors)
    generate_report(results, f'results/stress_test_2024_{month}.csv')
```

### Single Scenario Validation

```python
from pypsa_nza_dispatch import validate_single_scenario

diagnostics = validate_single_scenario(
    network,
    scaling_factor=1.25,  # +25% demand
    solver_name='highs'
)

print(f"Status: {diagnostics['status']}")
print(f"Load shed: {diagnostics['load_shed_fraction']*100:.1f}%")
```

## Workflow Integration

This tool fits into the broader capacity expansion workflow:

```
1. nza_cx_net.py          → Build base networks with demand
2. nza_cx_customize.py    → Add profiles and costs
3. nza-dispatch-validate  → Validate capacity adequacy ← YOU ARE HERE
4. nza_cx_optimize.py     → Run capacity expansion
5. nza-dispatch-validate  → Re-validate expanded network
```

## Troubleshooting

### "Network not found" error

**Problem:** Network directory doesn't exist
**Solution:**
1. Verify networks built: `ls {root}/cases/reference/2024/`
2. Check year and month are correct
3. Ensure networks are fully customized (not just base topology)

### Optimization fails

**Problem:** Solver cannot find solution
**Solutions:**
1. Check solver is installed: `python -c "import highspy"`
2. Try different solver: `--solver glpk`
3. Verify network has no structural issues
4. Check generator p_max_pu profiles are active (not all zeros)

### All runs show INADEQUATE

**Problem:** Even base year (1.0 scaling) fails
**Solutions:**
1. Verify base network is valid (can serve base year demand)
2. Check generator capacities are reasonable
3. Ensure renewable profiles are loaded correctly
4. Verify load data is sensible

### Memory issues

**Problem:** Out of memory with many scenarios
**Solutions:**
1. Test fewer scaling factors: `--max-year 2035`
2. Use single month instead of all 12
3. Reduce temporal resolution (half-hourly → hourly)

## Testing

Run the test suite:
```bash
pytest
```

With coverage:
```bash
pytest --cov=pypsa_nza_dispatch
```

## Contributing

This is research code for a PhD thesis. Issues and pull requests welcome but response may be limited during active research periods.

## License

MIT License - See LICENSE file for details

## Citation

If you use this tool in your research, please cite:

```bibtex
@software{bruneau2025pypsa_nza_dispatch,
  author = {Bruneau, Phillippe},
  title = {PyPSA-NZA Dispatch Validation},
  year = {2025},
  url = {https://github.com/yourusername/pypsa-nza-dispatch-validation}
}
```

## Support

For questions or issues:
1. Check the troubleshooting section above
2. Review the example scripts in `scripts/`
3. Open an issue on GitHub

## Acknowledgments

Built with:
- [PyPSA](https://pypsa.org/) - Python for Power System Analysis
- [HiGHS](https://highs.dev/) - High-performance open-source solver
- MBIE demand projections for New Zealand
