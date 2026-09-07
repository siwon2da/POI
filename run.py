#!/usr/bin/env python3
"""설치 없이 실행하는 진입점.  python run.py run examples/hello.poi"""
import sys

from poi.cli import main

if __name__ == "__main__":
    sys.exit(main())
