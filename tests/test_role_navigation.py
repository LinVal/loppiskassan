from pathlib import Path

def test_role_navigation_shell():
    root=Path(__file__).resolve().parents[1]
    html=(root/'static/admin-shell.html').read_text()
    assert 'id="roleSelector"' in html
    assert 'loppiskassan_demo_role' in html
    assert 'allowedViews()' in html
    assert '["cashier", "Kassan"' in html
    assert 'Påverkar endast menyn' in html
    source=(root/'sellers.py').read_text()
    assert "@router.get('/app')" in source
