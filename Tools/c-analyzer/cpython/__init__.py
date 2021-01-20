
import os.path
import sys
TOOL_ROOT = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
DATA_DIR = TOOL_ROOT
REPO_ROOT = os.path.dirname(os.path.dirname(TOOL_ROOT))
INCLUDE_DIRS = [os.path.join(REPO_ROOT, name) for name in ['Include']]
SOURCE_DIRS = [os.path.join(REPO_ROOT, name) for name in ['Python', 'Parser', 'Objects', 'Modules']]
PYTHON = sys.executable
del sys
del os
