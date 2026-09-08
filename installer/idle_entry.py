import sys

from poi.cli import main

# poi-idle.exe [파일.poi] — 인자를 그대로 idle 뒤에 넘긴다.
raise SystemExit(main(["idle", *sys.argv[1:]]))
