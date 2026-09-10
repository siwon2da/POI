from poi.packager import run_embedded_app

result = run_embedded_app()
if result is None:
    from poi.cli import main
    result = main()
raise SystemExit(result)
