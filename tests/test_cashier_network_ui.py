from pathlib import Path


def test_cashier_network_indicator_and_recovery():
    page = (Path(__file__).resolve().parents[1] / "static" / "index.html").read_text()
    assert 'id="connectionIndicator"' in page
    assert "async function probeConnection()" in page
    assert "setInterval(probeConnection,10000)" in page
    assert "const state=await api('/api/sessions/'+sid+'/status')" in page
    assert "existing||await api('/api/sessions/'+sid+'/sale'" in page
    assert "localStorage.setItem(draftKey" in page
    assert "Skarpt läge. Starta ett nytt köp" in page
