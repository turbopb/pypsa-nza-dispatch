# Quick Start Guide

Get up and running with pypsa-nza-dispatch in 5 minutes.

## 1. Install

```bash
# Clone repository
git clone https://github.com/yourusername/pypsa-nza-dispatch-validation.git
cd pypsa-nza-dispatch-validation

# Install in editable mode
pip install -e .

# Install HiGHS solver (free, open source)
pip install highspy
```

## 2. Configure

Edit `config/dispatch_config.yaml`:

```yaml
paths:
  # Point to your analysis directory
  root: "C:/Users/Public/Documents/Thesis/analysis"  # Windows
  # root: "/home/pbrun/thesis/analysis"              # Linux
```

## 3. Verify Networks Exist

Check that you have pre-built networks:

```bash
ls {your_root}/cases/reference/2024/apr_2024/
```

Should contain: `buses.csv`, `generators.csv`, `lines.csv`, etc.

## 4. Run

**Basic stress test:**
```bash
nza-dispatch-validate \
    --year 2024 \
    --month apr \
    --config config/dispatch_config.yaml
```

**Test specific growth:**
```bash
nza-dispatch-validate \
    --year 2024 \
    --month apr \
    --growth 25.0 \
    --config config/dispatch_config.yaml
```

## 5. View Results

Results saved to: `{your_root}/results/dispatch_validation/stress_test_reference_2024_apr.csv`

Open in Excel/pandas to analyze:
- When does system first fail?
- What type of bottleneck?
- Which buses shed load?

## Common Issues

**"Network not found"**
- Run `nza_cx_net.py` and `nza_cx_customize.py` first
- Verify year and month are correct

**"Optimization failed"**
- Check solver installed: `python -c "import highspy"`
- Try different solver: `--solver glpk`

**Need help?**
- See full README.md
- Check scripts/run_stress_test.py example
- Open GitHub issue

## What's Next?

- Test different months: `--month jul` (winter peak)
- Test different years: `--year 2025`
- Test further into future: `--max-year 2050`
- Write Python scripts for batch processing (see `scripts/run_stress_test.py`)
