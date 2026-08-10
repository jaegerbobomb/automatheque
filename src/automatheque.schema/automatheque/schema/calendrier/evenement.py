# -*- coding: utf-8 -*-
"""Evenement : ce qui a eu lieu, quand, et où.

La classe est une **structure pure** : elle ne parle ni à un serveur CalDAV,
ni à un fichier iCalendar. La conversion depuis et vers un `VEVENT` iCalendar
se fait à la frontière, par :meth:`Evenement.depuis_vevent` et
:meth:`Evenement.vers_vevent`, qui n'importent `vobject` qu'au moment de
l'appel. Le paquet reste donc installable — et `Evenement` utilisable — sans
`vobject`.

Pour disposer de la conversion :

```bash
pip install "automatheque.schema[calendrier]"
```
"""

from datetime import datetime, timezone
from typing import List, Optional

import attr

from automatheque.schema.temps import UTC, en_datetime

# Champs iCalendar repris tels quels dans la structure. L'ordre est celui du
# VEVENT, pour que la correspondance se lise d'un coup d'œil.
_CHAMPS_VEVENT = (
    ("uid", "uid"),
    ("summary", "titre"),
    ("location", "lieu"),
    ("description", "description"),
)


def _en_datetime(valeur):
    """Ramène une date iCalendar à une `datetime` tz-aware.

    Un `VEVENT` « journée entière » porte une `date` nue ; une `datetime` peut
    arriver naïve. **Ici** — un calendrier iCalendar — la politique est de les
    supposer UTC pour qu'elles restent comparables aux événements horodatés :
    on l'explicite au point d'appel (`suppose=UTC`), la primitive partagée
    `schema.temps.en_datetime` ne stampant, elle, jamais rien en douce. Cf. #48.
    """
    if valeur is None:
        return None
    return en_datetime(valeur, suppose=UTC)


@attr.s
class Evenement:
    """Un événement de calendrier.

    `etag` et `url` sont les deux attributs que CalDAV attache à la ressource
    (respectivement sa version et son adresse). Ils n'ont pas de sens hors
    d'un serveur, mais les transporter ici évite de trimballer un couple
    (événement, métadonnées de transport) dans tout le code appelant.
    """

    titre: Optional[str] = attr.ib(default=None, kw_only=True)
    date_debut: Optional[datetime] = attr.ib(
        default=None, kw_only=True, converter=_en_datetime
    )
    date_fin: Optional[datetime] = attr.ib(
        default=None, kw_only=True, converter=_en_datetime
    )
    lieu: Optional[str] = attr.ib(default=None, kw_only=True)
    description: Optional[str] = attr.ib(default=None, kw_only=True)
    uid: Optional[str] = attr.ib(default=None, kw_only=True)

    # Attributs spécifiques à CalDAV :
    etag: Optional[str] = attr.ib(default=None, kw_only=True)
    url: Optional[str] = attr.ib(default=None, kw_only=True)

    @property
    def date_fin_abregee(self) -> List[int]:
        """Ce qui distingue la date de fin de la date de début.

        Renvoie la liste des composantes — année, mois, jour — qui diffèrent
        entre le début et la fin. Ex : `[4, 12]` pour un événement du
        2018-03-14 au 2018-04-12, dont on n'a besoin d'écrire que « 04-12 ».

        Sert à abréger l'affichage d'une période : on pourrait le faire avec
        des règles de renommage, mais l'avoir ici simplifie les gabarits.
        Renvoie une liste vide si l'une des deux dates manque.
        """
        if not self.date_debut or not self.date_fin:
            return []

        abrege = []
        if self.date_debut.year != self.date_fin.year:
            abrege.append(self.date_fin.year)
        if self.date_debut.month != self.date_fin.month:
            abrege.append(self.date_fin.month)
        if self.date_debut.day != self.date_fin.day:
            abrege.append(self.date_fin.day)
        return abrege

    @classmethod
    def depuis_vevent(cls, vevent, etag=None, url=None) -> "Evenement":
        """Construit un `Evenement` depuis un `VEVENT` iCalendar.

        :param vevent: composant `VEVENT` de vobject, ou sa forme sérialisée
        :param etag: version de la ressource CalDAV, si elle vient d'un serveur
        :param url: adresse de la ressource CalDAV, idem
        :raise ImportError: si `vobject` n'est pas installé et qu'une chaîne
                            est passée (extra `calendrier`)
        """
        if isinstance(vevent, (str, bytes)):
            vevent = _lit_vobject(vevent)
            # `readOne` sur un VCALENDAR complet renvoie l'enveloppe : on
            # descend au premier VEVENT qu'elle contient.
            vevent = getattr(vevent, "vevent", vevent)

        champs = {
            nom: getattr(vevent, cle).value
            for cle, nom in _CHAMPS_VEVENT
            if hasattr(vevent, cle)
        }

        date_fin = None
        if hasattr(vevent, "dtend"):
            date_fin = vevent.dtend.value
        elif hasattr(vevent, "duration"):
            # TODO il nous faut un exemple et on calculera la date de fin
            # à partir de la date de début et la durée.
            # Reste le cas des événements récurrents ... :thinking_face:
            raise NotImplementedError(
                "VEVENT avec DURATION sans DTEND : pas encore géré"
            )

        return cls(
            date_debut=vevent.dtstart.value if hasattr(vevent, "dtstart") else None,
            date_fin=date_fin,
            etag=etag,
            url=url,
            **champs,
        )

    def vers_vevent(self):
        """Renvoie le `VEVENT` vobject correspondant à cet événement.

        Les champs vides ne sont pas écrits : un `VEVENT` ne porte que ce
        qu'on lui a donné.

        :raise ImportError: si `vobject` n'est pas installé (extra
                            `calendrier`)
        """
        vobject = _importe_vobject()
        vevent = vobject.newFromBehavior("vevent")
        for cle, nom in _CHAMPS_VEVENT:
            valeur = getattr(self, nom)
            if valeur is not None:
                vevent.add(cle).value = valeur
        if self.date_debut is not None:
            vevent.add("dtstart").value = _pour_vobject(self.date_debut)
        if self.date_fin is not None:
            vevent.add("dtend").value = _pour_vobject(self.date_fin)
        return vevent


def _importe_vobject():
    """Importe `vobject` en expliquant quoi installer s'il manque."""
    try:
        import vobject
    except ImportError as exc:  # pragma: no cover - dépend de l'installation
        raise ImportError(
            "La conversion iCalendar réclame vobject : "
            'pip install "automatheque.schema[calendrier]"'
        ) from exc
    return vobject


def _lit_vobject(serialise):
    """Dé-sérialise un composant iCalendar."""
    return _importe_vobject().readOne(serialise)


def _pour_vobject(valeur: datetime) -> datetime:
    """Rend une datetime sérialisable par vobject.

    vobject doit nommer le fuseau d'une datetime pour écrire son `TZID`, et
    ne sait pas le faire pour les décalages fixes de la bibliothèque standard
    (`datetime.timezone`) : il lève `Unable to guess TZID`. Or c'est
    précisément ce que pose le convertisseur d'`Evenement`. On ramène donc ces
    dates à l'UTC de vobject, qu'il sérialise en `Z` — même instant, notation
    sans ambiguïté. Les fuseaux nommés (pytz…) passent intacts, pour conserver
    leur `TZID`.
    """
    if isinstance(valeur.tzinfo, timezone):
        return valeur.astimezone(_importe_vobject().icalendar.utc)
    return valeur
