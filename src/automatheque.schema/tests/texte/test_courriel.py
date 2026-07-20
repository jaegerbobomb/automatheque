from datetime import datetime

import attr
import pytest  # type: ignore
from automatheque.schema.texte.courriel import Courriel, maintenant


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


def test_date_envoi_utilise_une_fabrique():
    """#25 : ``_date_envoi`` doit être une *fabrique*, pas une constante figée.

    Avec ``default=datetime.now()`` la date était évaluée une seule fois à la
    définition de la classe et partagée par toutes les instances. Ce test
    échouerait sur l'ancien code (le ``default`` était un ``datetime``).
    """
    champ = attr.fields_dict(Courriel)["_date_envoi"]
    assert isinstance(champ.default, attr.Factory)  # type: ignore[arg-type]
    assert champ.default.factory is maintenant


def test_date_envoi_horodatage_par_instance():
    """Deux courriels obtiennent chacun leur propre horodatage tz-aware."""
    c1 = Courriel(sujet="a")
    c2 = Courriel(sujet="b")
    assert c1._date_envoi.tzinfo is not None
    assert c2._date_envoi.tzinfo is not None
    # Objets distincts (pas la même constante partagée), et croissants.
    assert c1._date_envoi <= c2._date_envoi


def test_date_envoi_format_rfc5322_tz_aware():
    """La date rendue porte un offset explicite (``+0000`` en UTC)."""
    c = Courriel(sujet="x")
    assert c.date_envoi.endswith("+0000")


def test_date_envoi_datetime_naif_retrocompat():
    """Un ``datetime`` naïf affecté manuellement reste formatable (heure locale)."""
    c = Courriel(sujet="x")
    c._date_envoi = datetime(2020, 1, 2, 3, 4, 5)  # naïf
    rendu = c.date_envoi
    assert "02 Jan 2020" in rendu
