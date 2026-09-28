"""Turn Kani AutoHarness output into validated, versioned JSON.

The package knows about Kani's output and nothing about any frontend.
Its only product is the `data/` directory described in docs/data-contract.md.
"""

__version__ = "0.1.0"

# Version of the published JSON contract (bundled schema/*.schema.json).
# Bump MAJOR for breaking changes, MINOR for additive fields.
SCHEMA_VERSION = "1.0.0"
