"""
Utility functions for PyPSA-NZA dispatch validation.

Adapted from nza_cx_module.py - contains only essential functions needed
for dispatch validation.
"""

import os
import yaml
from pathlib import Path
from typing import Dict


def load_config(config_file: str) -> Dict:
    """
    Load YAML configuration file.

    Parameters
    ----------
    config_file : str
        Path to YAML configuration file

    Returns
    -------
    dict
        Configuration dictionary

    Raises
    ------
    FileNotFoundError
        If config file not found
    yaml.YAMLError
        If YAML parsing fails
    """
    if not os.path.exists(config_file):
        raise FileNotFoundError(f"Configuration file not found: {config_file}")

    try:
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
        return config
    except yaml.YAMLError as e:
        raise yaml.YAMLError(f"Error parsing YAML file: {e}")


def resolve_path(base_path: str, relative_path: str) -> Path:
    """
    Resolve a relative path from a base path.

    Parameters
    ----------
    base_path : str
        Base directory path
    relative_path : str
        Relative path to resolve

    Returns
    -------
    Path
        Resolved absolute path
    """
    return Path(base_path) / relative_path


def validate_data_paths(config: Dict) -> bool:
    """
    Validate that required data paths exist.

    Parameters
    ----------
    config : dict
        Configuration dictionary with 'paths' section

    Returns
    -------
    bool
        True if all required paths exist

    Raises
    ------
    ValueError
        If required paths are missing or don't exist
    """
    if 'paths' not in config:
        raise ValueError("Configuration missing 'paths' section")

    if 'root' not in config['paths']:
        raise ValueError("Configuration missing 'paths.root'")

    root = Path(config['paths']['root'])
    if not root.exists():
        raise ValueError(f"Data root directory does not exist: {root}")

    # Check critical paths
    required_dirs = ['dirpath_static', 'dirpath_costs']
    missing = []

    for dir_key in required_dirs:
        if dir_key not in config['paths']:
            missing.append(dir_key)
            continue

        dir_path = root / config['paths'][dir_key]
        if not dir_path.exists():
            missing.append(f"{dir_key} -> {dir_path}")

    if missing:
        raise ValueError(f"Required data directories not found: {missing}")

    return True


def get_network_path(config: Dict, year: int, month: str) -> Path:
    """
    Get path to network directory.

    Parameters
    ----------
    config : dict
        Configuration dictionary
    year : int
        Network year
    month : str
        Month abbreviation (e.g., 'jan', 'apr')

    Returns
    -------
    Path
        Path to network directory
    """
    root = Path(config['paths']['root'])
    network_path = root / f"cases/reference/{year}/{month}_{year}"
    return network_path


def print_heading(heading: str, underline: bool = False, char: str = '='):
    """
    Print a formatted heading.

    Parameters
    ----------
    heading : str
        Heading text
    underline : bool
        Whether to underline the heading
    char : str
        Character to use for underline
    """
    print(f"\n{heading}")
    if underline:
        print(char * len(heading))


def format_mwh(mwh: float) -> str:
    """
    Format MWh value for display.

    Parameters
    ----------
    mwh : float
        Energy in MWh

    Returns
    -------
    str
        Formatted string
    """
    if mwh >= 1e6:
        return f"{mwh/1e6:.2f} TWh"
    elif mwh >= 1e3:
        return f"{mwh/1e3:.2f} GWh"
    else:
        return f"{mwh:.1f} MWh"


def format_mw(mw: float) -> str:
    """
    Format MW value for display.

    Parameters
    ----------
    mw : float
        Power in MW

    Returns
    -------
    str
        Formatted string
    """
    if mw >= 1e3:
        return f"{mw/1e3:.2f} GW"
    else:
        return f"{mw:.1f} MW"
