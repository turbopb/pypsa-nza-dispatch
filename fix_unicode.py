"""
Fix Unicode characters in pypsa-nza-dispatch that break on Windows.
"""

from pathlib import Path
import re

files_to_fix = [
    'pypsa_nza_dispatch/network.py',
    'pypsa_nza_dispatch/cli.py',
    'pypsa_nza_dispatch/validation.py',
]

for filepath in files_to_fix:
    p = Path(filepath)
    if not p.exists():
        print(f"Skipping {filepath} - not found")
        continue
    
    print(f"Processing {filepath}...")
    
    content = p.read_text(encoding='utf-8')
    
    # Replace common Unicode characters
    replacements = {
        r'\\u2713': '',  # Checkmark
        r'\\u2717': 'X',  # X mark
        r'\\u2022': '*',  # Bullet
        r'\\u2192': '->',  # Right arrow
    }
    
    original = content
    for pattern, replacement in replacements.items():
        content = re.sub(pattern, replacement, content)
    
    if content != original:
        p.write_text(content, encoding='utf-8')
        print(f"  Fixed {filepath}")
    else:
        print(f"  No changes needed in {filepath}")

print("\nDone! Now reinstall:")
print("pip install -e . --break-system-packages")