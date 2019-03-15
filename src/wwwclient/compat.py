import sys
IS_PYTHON3 = sys.version_info[0] > 2
if IS_PYTHON3:
	from .compat3 import *
else:
	from .compat2 import *
# EOF
