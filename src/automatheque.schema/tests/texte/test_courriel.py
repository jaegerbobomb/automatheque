from automatheque.schema.texte.courriel import Courriel

def test_courriel():
    c = Courriel()
    assert isinstance(c, Courriel)
