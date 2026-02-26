"""
Fix ALL Unicode characters in ALL Python files.
"""

from pathlib import Path

# Find all Python files
python_files = list(Path('pypsa_nza_dispatch').rglob('*.py'))

print(f"Found {len(python_files)} Python files")

for filepath in python_files:
    try:
        content = filepath.read_text(encoding='utf-8')
        original = content
        
        # Replace all Unicode escape sequences
        content = content.replace('\\u2713', '')  # Checkmark
        content = content.replace('\\u2717', 'X')  # X mark
        content = content.replace('\\u2022', '*')  # Bullet
        content = content.replace('\\u2192', '->')  # Arrow
        
        if content != original:
            filepath.write_text(content, encoding='utf-8')
            print(f"  Fixed: {filepath}")
    except Exception as e:
        print(f"  Error in {filepath}: {e}")

print("\nDone! Reinstalling...")
import subprocess
subprocess.run(['pip', 'install', '-e', '.', '--break-system-packages'], check=True)
print("\n? Package reinstalled")