"""
Patch dla config.py - dodaje brakujące parametry
Uruchom przed deployment: python deployment/config_patch.py
"""

import re

CONFIG_PATH = "../config.py"

# Parametry do dodania na końcu pliku
MISSING_PARAMS = """
# Vector configuration (używane w qdrant_setup.py)
DENSE_VECTOR_SIZE = 768
DENSE_DISTANCE_METRIC = "Cosine"
COLBERT_VECTOR_SIZE = 96
COLBERT_DISTANCE_METRIC = "Cosine"

# Memory optimization
ENABLE_BINARY_QUANTIZATION = True
DENSE_VECTORS_ON_DISK = True
COLBERT_VECTORS_ON_DISK = False
QUANTIZATION_ALWAYS_RAM = True
"""

# Parametry do zmiany
CHANGES = {
    'ENABLE_GROUPING = False': 'ENABLE_GROUPING = True',
    'GROUP_BY_FIELD = "post_id"': 'GROUP_BY_FIELD = "document_id"',
    'GROUP_SIZE = 3': 'GROUP_SIZE = 1  # max 1 chunk per article',
}


def patch_config():
    """Apply patches to config.py"""
    with open(CONFIG_PATH, 'r') as f:
        content = f.read()

    # Apply changes
    for old, new in CHANGES.items():
        if old in content:
            content = content.replace(old, new)
            print(f"✅ Changed: {old} → {new}")
        else:
            print(f"⚠️  Not found: {old}")

    # Add missing params if not present
    if "DENSE_VECTOR_SIZE" not in content:
        content += "\n" + MISSING_PARAMS
        print("✅ Added missing vector configuration parameters")
    else:
        print("⚠️  Vector params already exist, skipping")

    # Write back
    with open(CONFIG_PATH, 'w') as f:
        f.write(content)

    print("\n✅ config.py patched successfully!")


if __name__ == "__main__":
    print("🔧 Patching config.py...\n")
    patch_config()
