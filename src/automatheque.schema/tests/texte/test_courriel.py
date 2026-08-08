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


def test_constructeur_valide_l_emetteur_comme_le_setter():
    """Le constructeur ne doit pas court-circuiter la validation des adresses."""
    with pytest.raises(ValueError):
        Courriel(sujet="s", emetteur="pas-un-email")


def test_constructeur_formate_un_emetteur_tuple():
    """Un tuple `(nom, adresse)` est normalisé en chaîne RFC 5322, comme via
    le setter — pas laissé brut."""
    c = Courriel(sujet="s", emetteur=("Bob", "bob@x.com"))
    assert c.emetteur == "Bob <bob@x.com>"


def test_constructeur_emetteur_none_reste_permis():
    """`emetteur=None` (le défaut) n'est pas validé : il est rempli plus tard."""
    assert Courriel(sujet="s").emetteur is None


def test_constructeur_valide_les_destinataires():
    """Les destinataires passés au constructeur sont validés/normalisés."""
    c = Courriel(sujet="s", destinataires=["Bob <bob@x.com>", ("Ana", "ana@x.com")])
    assert c.destinataires == ["Bob <bob@x.com>", "Ana <ana@x.com>"]
    with pytest.raises(ValueError):
        Courriel(sujet="s", destinataires=["pas-un-email"])


def test_destinataire_chaine_unique_n_est_pas_eclatee_en_caracteres():
    """Régression : `destinataires = "solo@x.com"` validait `s`, `o`, `l`…"""
    c = Courriel(sujet="s")
    c.destinataires = "solo@x.com"
    assert c.destinataires == ["solo@x.com"]
