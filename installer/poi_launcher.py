import os
import sys

# 이 파일과 같은 폴더에 poi/ 패키지가 있다.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from poi.cli import main  # noqa: E402

raise SystemExit(main())
