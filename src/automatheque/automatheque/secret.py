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

import logging
import os
import shlex
from configparser import ConfigParser, NoOptionError, NoSectionError
from typing import List, Optional, Protocol, cast

import attr

from automatheque.conception.structures import MetaInstanceRegistre
from automatheque.greffon import FabriqueGreffon, Greffon, signale_appel
from automatheque.greffon.capacite import Capacite

#: Chaîne affichée à la place d'un secret dans les représentations textuelles.
CAVIARDAGE = "***"


@attr.s(repr=False, eq=False)
class Secret(metaclass=MetaInstanceRegistre):
    """Enveloppe une valeur sensible dont le ``repr``/``str`` est **caviardé**.

    La valeur réelle n'est accessible que via :meth:`reveler` — jamais via
    ``str()``, ``repr()``, un f-string ou le logging, qui affichent tous
    :data:`CAVIARDAGE`. Cela évite les fuites accidentelles dans les logs et les
    tracebacks.

    Patron **Registre d'instances (faibles)** : via
    :class:`~automatheque.conception.structures.MetaInstanceRegistre`, chaque
    ``Secret`` créé est référencé **faiblement** dans un registre — sans
    prolonger sa vie. :class:`FiltreCaviardage` s'en sert pour caviarder toute
    valeur de secret **vivant** qui apparaîtrait dans un message de log (rien à
    enregistrer à la main). ``eq=False`` rend l'objet hachable (identité), requis
    par le registre.
    """

    _valeur: str = attr.ib()

    def reveler(self) -> str:
        """Renvoie la valeur réelle (à n'utiliser qu'au point d'usage)."""
        return self._valeur

    def __str__(self) -> str:
        return CAVIARDAGE

    def __repr__(self) -> str:
        return "Secret({})".format(CAVIARDAGE)


def _secrets_vivants() -> List["Secret"]:
    """Renvoie les :class:`Secret` encore vivants (registre d'instances faibles)."""
    return Secret._instances(inclure_enfants=True)


class FiltreCaviardage(logging.Filter):
    """Filtre de logging qui **caviarde** les valeurs des :class:`Secret` vivants.

    À poser sur un **handler** (et non un logger) pour couvrir aussi les
    enregistrements *propagés* des loggers enfants — cf. :func:`installe_caviardage`
    dans :mod:`automatheque.log`. Si la valeur révélée d'un secret vivant apparaît
    dans le message rendu, elle est remplacée par :data:`CAVIARDAGE`.

    Défense **en profondeur** : la première ligne reste de ne jamais logger un
    secret en clair (utiliser :class:`Secret`, dont ``str``/``repr`` sont déjà
    caviardés). Ce filtre rattrape les fuites indirectes (une valeur brute
    ``reveler()`` journalisée par erreur, un secret concaténé dans un message…).

    Note : le filtre remplace des **sous-chaînes littérales** ; une valeur très
    courte peut donc caviarder large. Les vrais secrets (mots de passe, jetons)
    sont longs, ce qui rend le cas anecdotique — raison de plus pour ne pas
    utiliser de secret trivial.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        valeurs = [v for v in (s.reveler() for s in _secrets_vivants()) if v]
        if not valeurs:
            return True
        message = record.getMessage()
        caviarde = message
        for valeur in valeurs:
            if valeur in caviarde:
                caviarde = caviarde.replace(valeur, CAVIARDAGE)
        if caviarde != message:
            # On fige le message rendu (et on neutralise args) pour que le
            # caviardage tienne quel que soit le handler en aval.
            record.msg = caviarde
            record.args = ()
        return True


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


#: **Fabrique locale** des greffons résolveurs par défaut (patron **Fabrique**,
#: comme ``fabrique_greffon``). Locale pour ne pas encombrer la fabrique globale
#: des greffons applicatifs. ``active(cle, identifiant=…)`` **dédoublonne par
#: identifiant** : on réutilise ainsi un unique greffon par source, plutôt que
#: d'en recréer un à chaque appel de :func:`recup_secret` (le registre des
#: greffons est persistant).
_fabrique = FabriqueGreffon()
_fabrique.charge_monteurs(
    [GreffonSecretEnv, GreffonSecretConfig, GreffonSecretKeyring, GreffonSecretCommande]
)


def _resolveur_defaut(cle_monteur: str, **kwargs) -> Optional[ResoudreSecret]:
    """Active (une fois, dédup par ``identifiant``) un greffon résolveur par défaut.

    ``active`` renvoie ``None`` si l'activation échoue — cas défensif : ces
    greffons ne peuvent pas échouer à la construction.
    """
    return cast("Optional[ResoudreSecret]", _fabrique.active(cle_monteur, **kwargs))


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
        defauts = [_resolveur_defaut("secretenv", identifiant="secret:env")]
        if config is not None:
            defauts.append(
                _resolveur_defaut(
                    "secretconfig",
                    identifiant="secret:config:{}".format(id(config)),
                    source=config,
                )
            )
        resolveurs = [r for r in defauts if r is not None]
    for resolveur in resolveurs:
        valeur = resolveur.resout_secret(cle)
        if valeur is not None:
            return Secret(valeur)
    return None
