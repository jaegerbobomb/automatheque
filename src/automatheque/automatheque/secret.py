# -*- coding: utf-8 -*-
"""Gestion des secrets : objet :class:`Secret` **caviardé** + résolution par greffons.

But (cf. #8) : ne jamais laisser fuiter un identifiant/jeton dans les logs ou les
tracebacks, et centraliser leur récupération (variable d'environnement,
configuration, trousseau système, commande externe) derrière une API unique.

Les sources de secrets sont des **greffons** (cf. :mod:`automatheque.greffon`)
qui rendent la capacité :class:`ResoudreSecret` : on privilégie ainsi le
système de greffons pour toute source enfichable, plutôt qu'un mécanisme ad hoc.

.. code-block:: python

    from automatheque.secret import recup_secret

    mdp = recup_secret("factrice.smtp.mdp", config=ma_config)
    if mdp is not None:
        serveur.login(user, mdp.reveler())  # .reveler() UNIQUEMENT au point d'usage

``str(mdp)``, ``repr(mdp)``, un f-string ou le logging affichent tous ``***`` :
la valeur réelle n'est accessible que via :meth:`Secret.reveler`.
"""

import os
import shlex
from configparser import ConfigParser, NoOptionError, NoSectionError
from typing import Any, Dict, List, Optional, Protocol

import attr

from automatheque.greffon import Greffon, signale_appel
from automatheque.greffon.capacite import Capacite

#: Chaîne affichée à la place d'un secret dans les représentations textuelles.
CAVIARDAGE = "***"


@attr.s(repr=False, eq=False)
class Secret:
    """Enveloppe une valeur sensible dont le ``repr``/``str`` est **caviardé**.

    La valeur réelle n'est accessible que via :meth:`reveler` — jamais via
    ``str()``, ``repr()``, un f-string ou le logging, qui affichent tous
    :data:`CAVIARDAGE`. Cela évite les fuites accidentelles dans les logs et les
    tracebacks.
    """

    _valeur: str = attr.ib()

    def reveler(self) -> str:
        """Renvoie la valeur réelle (à n'utiliser qu'au point d'usage)."""
        return self._valeur

    def __str__(self) -> str:
        return CAVIARDAGE

    def __repr__(self) -> str:
        return "Secret({})".format(CAVIARDAGE)


class ResoudreSecret(Capacite, Protocol):
    """Capacité : **résoudre** une clé logique en la valeur brute d'un secret.

    Un greffon qui déclare cette capacité (``CAPACITES = [ResoudreSecret]``)
    implémente :meth:`resout_secret`, renvoyant la valeur (chaîne brute) ou
    ``None`` s'il ne connaît pas la clé. :func:`recup_secret` enveloppe ensuite
    cette valeur dans un :class:`Secret`.
    """

    def resout_secret(self, cle: str) -> Optional[str]: ...


@attr.s(eq=False)
class GreffonSecretEnv(Greffon):
    """Greffon **variable d'environnement**.

    ``factrice.smtp.mdp`` → variable ``FACTRICE_SMTP_MDP`` (majuscules, ``.`` et
    ``-`` remplacés par ``_``).
    """

    CAPACITES = [ResoudreSecret]

    @signale_appel
    def resout_secret(self, cle: str) -> Optional[str]:
        nom = cle.upper().replace(".", "_").replace("-", "_")
        return os.environ.get(nom)


@attr.s(eq=False)
class GreffonSecretConfig(Greffon):
    """Greffon **configuration** : ``section.option`` → ``config.get(...)``.

    La clé est coupée sur le **dernier** point : ``factrice.smtp.mdp`` →
    section ``factrice.smtp``, option ``mdp``. Par défaut le greffon lit sa
    propre configuration (``self.config``) ; on peut lui imposer un
    :class:`~configparser.ConfigParser` précis via ``source``.
    """

    CAPACITES = [ResoudreSecret]

    source: Optional[ConfigParser] = attr.ib(
        default=None,
        kw_only=True,
        validator=attr.validators.optional(attr.validators.instance_of(ConfigParser)),
    )

    @signale_appel
    def resout_secret(self, cle: str) -> Optional[str]:
        conf = self.source if self.source is not None else self.config
        section, _, option = cle.rpartition(".")
        if not section or not option:
            return None
        try:
            return conf.get(section, option)
        except (NoSectionError, NoOptionError):
            return None


@attr.s(eq=False)
class GreffonSecretKeyring(Greffon):
    """Greffon **trousseau système** (dépendance optionnelle ``keyring``).

    Si ``keyring`` n'est pas installé, le greffon est **neutre** (renvoie
    ``None``) plutôt que d'échouer.
    """

    CAPACITES = [ResoudreSecret]

    service: str = attr.ib(default="automatheque", kw_only=True)

    @signale_appel
    def resout_secret(self, cle: str) -> Optional[str]:
        try:
            import keyring
        except ImportError:
            return None
        return keyring.get_password(self.service, cle)


@attr.s(eq=False)
class GreffonSecretCommande(Greffon):
    """Greffon **commande externe** : la sortie standard de la commande EST le secret.

    ``gabarit`` peut contenir ``{cle}`` (substituée). La commande est découpée
    avec :func:`shlex.split` et exécutée **sans shell** via ``Executant``
    (``subprocess.run(liste)``) — donc pas d'injection.
    """

    CAPACITES = [ResoudreSecret]

    gabarit: str = attr.ib(default="", kw_only=True)

    @signale_appel
    def resout_secret(self, cle: str) -> Optional[str]:
        from automatheque.util.dependances_externes import Executant

        cmd, *args = shlex.split(self.gabarit.format(cle=cle))
        sortie = Executant(cmd).exec(*args, encoding="utf-8").stdout or ""
        return sortie.strip("\n") or None


#: Cache des greffons résolveurs *par défaut* : le registre des greffons est
#: **persistant** (toute instance y reste), donc on réutilise un unique greffon
#: par configuration plutôt que d'en créer un à chaque appel de :func:`recup_secret`.
_RESOLVEURS: Dict[Any, ResoudreSecret] = {}


def _resolveur(cle_cache: Any, fabrique) -> ResoudreSecret:
    """Renvoie le greffon résolveur mis en cache pour ``cle_cache`` (le crée sinon)."""
    resolveur = _RESOLVEURS.get(cle_cache)
    if resolveur is None:
        resolveur = _RESOLVEURS[cle_cache] = fabrique()
    return resolveur


def recup_secret(
    cle: str,
    config: Optional[ConfigParser] = None,
    resolveurs: Optional[List[ResoudreSecret]] = None,
) -> Optional[Secret]:
    """Résout ``cle`` via des greffons **dans l'ordre** ; premier gagnant.

    Ordre par défaut : **variable d'environnement** (:class:`GreffonSecretEnv`)
    puis, si ``config`` est fourni, la **configuration**
    (:class:`GreffonSecretConfig`). Pour un ordre ou des sources personnalisés
    (trousseau, commande externe…), passer ``resolveurs`` : une liste ordonnée
    de greffons rendant la capacité :class:`ResoudreSecret` (p. ex.
    :class:`GreffonSecretKeyring`, :class:`GreffonSecretCommande`).

    :returns: un :class:`Secret` (caviardé) ou ``None`` si aucun greffon ne
        fournit la clé.
    """
    if resolveurs is None:
        resolveurs = [_resolveur("env", GreffonSecretEnv)]
        if config is not None:
            resolveurs.append(
                _resolveur(
                    ("config", id(config)),
                    lambda: GreffonSecretConfig(source=config),
                )
            )
    for resolveur in resolveurs:
        valeur = resolveur.resout_secret(cle)
        if valeur is not None:
            return Secret(valeur)
    return None
