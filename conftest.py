"""
conftest for services/memos.as tests.

Ensures the service directory is first on sys.path so imports like `import app` resolve to
the correct package under `services/memos.as` (and not to stale backups or other folders).
"""

import os
import sys

HERE = os.path.abspath(os.path.dirname(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

# Also ensure local libs (apexsigma_core) are importable during tests
LIBS_APEX_PATH = os.path.join(HERE, "libs", "apexsigma-core")
if os.path.isdir(LIBS_APEX_PATH) and LIBS_APEX_PATH not in sys.path:
    sys.path.insert(0, LIBS_APEX_PATH)
