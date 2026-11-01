from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def test_demo_is_client_only_and_separate():
    demo=(ROOT/'static/demo.html').read_text()
    live=(ROOT/'static/index.html').read_text()
    shell=(ROOT/'static/admin-shell.html').read_text()
    assert "let items=initial.map" in demo
    assert "let items=[],imageSrc='',selected=0;" in live
    assert "'/api/sessions/" not in demo
    assert "fetch('/api/" not in demo
    assert "Övningsköp" in demo
    assert "id=\"modeSelector\"" in shell
    assert "cashierMode==='demo'?'/demo':entry[3]" in shell
    assert "@router.get('/demo')" in (ROOT/'sellers.py').read_text()
