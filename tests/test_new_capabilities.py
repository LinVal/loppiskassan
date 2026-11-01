from pathlib import Path

def test_new_admin_endpoints_are_role_protected():
    from staff_auth import required_role
    assert required_role('/api/admin/register-reconciliation','GET') == 'admin'
    assert required_role('/api/admin/register-reconciliation','POST') == 'admin'
    assert required_role('/api/staff/me','GET') == 'cashier'
    assert required_role('/api/v4/sales','GET') == 'admin'
    assert required_role('/api/v5/events','GET') == 'admin'
    assert required_role('/api/cashier/recent-sales','GET') == 'cashier'


def test_cashier_evidence_and_navigation_are_present():
    root=Path(__file__).resolve().parents[1]
    server=(root/'server.py').read_text()
    ui=(root/'static/index.html').read_text()
    shell=(root/'static/admin-shell.html').read_text()
    assert 'CREATE TABLE IF NOT EXISTS item_evidence' in server
    assert 'photo_id:x.photoId||null' in ui
    assert 'ai_seller:x.aiSeller||null' in ui
    assert 'loadRecentSales' in ui
    assert '/register-reconciliation.html' in shell
    assert '/staff-management.html' in shell
