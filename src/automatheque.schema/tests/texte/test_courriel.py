import pytest  # type: ignore

from automatheque.schema.texte.courriel import Courriel


def test_courriel():
    c = Courriel(emetteur="src@mail.com", sujet="Sujet du mail")
    assert isinstance(c, Courriel)

    c.ajouter_destinataire("user@tld.com")
    assert c.destinataires == ["user@tld.com"]
    c.ajouter_destinataire("Toto <toto@tld.com>")
    assert c.destinataires == ["user@tld.com", "Toto <toto@tld.com>"]
    c.ajouter_destinataire(("Titi", "titi@tld.com"))
    assert c.destinataires == [
        "user@tld.com",
        "Toto <toto@tld.com>",
        "Titi <titi@tld.com>",
    ]

    with pytest.raises(ValueError) as err:
        c.destinataires = ["Faux faux-mail.com"]
    assert str(err.value) == "Adresse courriel invalide"
