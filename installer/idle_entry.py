import sys

from poi.packager import run_embedded_app

result = run_embedded_app()
if result is None:
    from poi.cli import main
    # poi-idle.exe [파일.poi] — 인자를 그대로 idle 뒤에 넘긴다.
    result = main(["idle", *sys.argv[1:]])
raise SystemExit(result)
