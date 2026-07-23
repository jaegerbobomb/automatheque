# -*- coding:utf-8 -*-
"""API phare d'automatheque : faciliter la création de scripts.

``script_automatheque`` accepte un ``argv`` (et un ``nom``) explicites pour ne
pas dépendre de ``sys.argv`` — utile **surtout pour tester** un script sans
bricoler cette variable globale (cf. :mod:`automatheque.essai`). Cf. #24.

Le format que l'on souhaite est le suivant :
```
'''Mon script

Usage:
  mon_script.py [--action] [--dry-run] [-v | -q] [--config=<fichier_config>]

Options:
  --action  Action realisée
  --dry-run  N'effectue aucune action définitive
  -v --verbose  Journalisation plus bavarde (DEBUG) ; répétable
  -q --quiet  Journalisation plus discrète (WARNING)
  --config=<fichier_config>  Fichier de configuration supplémentaire (ponctuel)
'''
__version__ = '0.1a'  # ou importer depuis mon_package.__version__

# La configuration est chargée en couches, sans rien déclarer ici :
#   ~/.config/automatheque/config.ini   (partagé entre scripts)
#   ~/.config/<mon_script>/config.ini   (propre à ce script ; surcharge)
#   --config <fichier>                  (ponctuel ; surcharge)

from automatheque.script import script  # alias court de script_automatheque

@script(__doc__, __version__)
def main(..., _script=None):
    # code à exécuter
    # _script est un objet `ScriptAutomatheque`
    if _script.dry_run:
        return  # rien de définitif en dry-run
    print(_script)

if __name__ == '__main__':
    main(...)
```
Cela déclenche les logs de début, de fin, parse les arguments etc. Si le script
déclare ``--dry-run``, ``-v``/``-q`` dans son usage, ils sont **câblés
automatiquement** : ``_script.dry_run`` et le niveau de log sont ajustés sans
code supplémentaire. Une interruption clavier (Ctrl-C) se solde par une sortie
propre (code 130) et toute exception non gérée est journalisée avant de remonter.

``script`` est un alias court de ``script_automatheque`` : les deux noms sont
équivalents et exportés depuis ``automatheque.script``.

Sous-commandes (via ``commandopt``) : on déclare des fonctions-commandes avec
``@commande([...])`` et on aiguille avec ``_script.execute_commande()``. Les
options internes d'automatheque (``--config``, ``--dry-run``, ``-v``/``-q``)
sont exclues de la sélection.
```
'''Usage:
  mon_script.py (--ajouter | --supprimer) [--config=<f>] [-v]
'''
from automatheque.script import script, commande

@commande(["--ajouter"])
def ajouter(arguments):
    ...

@commande(["--supprimer"])
def supprimer(arguments):
    ...

@script(__doc__, __version__)
def main(_script):
    return _script.execute_commande()
```

.. note::
   Historiquement ce module vivait dans ``automatheque.util.script``. Il a été
   promu au premier niveau (:mod:`automatheque.script`) car c'est l'API centrale
   du projet, pas un utilitaire bas niveau (#41). L'ancien emplacement reste
   importable via un shim qui émet un ``DeprecationWarning``.
"""

import datetime
import logging
import os
import re
import sys
from functools import wraps

import attr
import docopt

# Ré-exportés pour offrir une seule surface d'import aux scripts
# (`from automatheque.script import commande, Registry, NoCommandFoundError`).
from commandopt import (  # noqa: F401
    Command,
    NoCommandFoundError,
    Registry,
    commandopt,
)

from automatheque import constantes
from automatheque.configuration import charge_configuration
from automatheque.log import configure_logging_defaut, logger_existe

#: Options « internes » à automatheque : elles configurent le script (logging,
#: emplacement de config, simulation), elles ne le **routent** pas. On les
#: exclut donc de la sélection de commande commandopt (#39), sinon un
#: ``--config`` ou un ``-v`` ferait échouer l'appariement d'une commande.
OPTIONS_INTERNES = frozenset(
    {"--config", "--dry-run", "-v", "--verbose", "-q", "--quiet"}
)

#: Alias ergonomique de :func:`commandopt.commandopt` : ``@commande([...])`` se
#: lit mieux dans un script. Le nom d'origine reste disponible via commandopt.
commande = commandopt


def script_automatheque(chaine_docopt, version=None, argv=None, nom=None):
    """Decorateur pour ScriptAutomatheque.

    - signale le début et la fin du traitement
    - passe un objet ScriptAutomatheque à la fonction appelante

    :param argv: arguments de ligne de commande (**sans** le nom du programme).
        Défaut ``None`` = ``sys.argv``. Le fournir sert surtout à **tester** un
        script sans bricoler ``sys.argv`` (cf. :mod:`automatheque.essai`).
        Cf. #24.
    :param nom: nom du programme (utilisé pour ``nom_court`` et les logs). Défaut
        ``None`` = ``sys.argv[0]``. Cf. #24.
    """
    s = ScriptAutomatheque(
        nom=nom if nom is not None else sys.argv[0],
        chaine_docopt=chaine_docopt,
        version=version,
        argv=argv,
    )
    s.initialise()

    def decorateur(fonction):
        @wraps(fonction)
        def init_script(*args, **kwds):
            try:
                s.joli_titre()
                s.signale_debut_traitement()
                if s.dry_run:
                    s.logger.info(
                        "Mode --dry-run actif : aucune action définitive "
                        "ne devrait être effectuée."
                    )
                return fonction(_script=s, *args, **kwds)
            except KeyboardInterrupt:
                # Ctrl-C : sortie propre (code POSIX 130) plutôt qu'une
                # traceback. N'arrive jamais dans les tests (pas d'interruption).
                s.logger.warning("Interruption clavier (Ctrl-C) — arrêt.")
                raise SystemExit(130)
            except Exception:
                # On journalise l'erreur (avec sa traceback) puis on la laisse
                # remonter : code de sortie non nul + testabilité préservée.
                s.logger.exception("Le script s'est terminé sur une erreur.")
                raise
            finally:
                s.signale_fin_traitement()

        return init_script

    return decorateur


@attr.s(eq=False)
class ScriptAutomatheque:
    """Objet ScriptAutomatheque qui automatise la creation de scripts.

    Cet objet contient :
    - self.arguments : les arguments récupérés par docopt
    - self.config : automatiquement extraite de l'argument --config si présent
                    mergée avec la configuration d'automatheque
    - self.parametres : merge de arguments avec config
    - self.logger : logger pour les appels internes de ScriptAutomatheque

    ``eq=False`` : l'objet garde une sémantique d'**identité** (comparaison et
    hachage par référence), comme avant le passage à attrs — deux scripts ne
    sont jamais « égaux » par valeur, et l'objet reste hachable. Cf. #24.
    """

    nom = attr.ib()
    chaine_docopt = attr.ib(repr=False)  # trop longue pour le repr
    version = attr.ib(default=None)
    #: ``argv`` explicite (liste d'arguments **sans** le nom du programme) pour
    #: piloter le script sans dépendre de ``sys.argv`` — surtout pour le test
    #: (cf. :mod:`automatheque.essai`). Défaut ``None`` = docopt lit
    #: ``sys.argv``. Cf. #24.
    argv = attr.ib(default=None)
    nom_court = attr.ib(init=False)
    arguments = attr.ib(init=False, default=None)
    config = attr.ib(init=False, default=None)
    #: Vrai si le script a été appelé avec ``--dry-run`` (câblé automatiquement
    #: si l'option figure dans l'usage docopt). Au script d'en tenir compte pour
    #: ne rien modifier de définitif.
    dry_run = attr.ib(init=False, default=False)
    _debut = attr.ib(init=False, default=None, repr=False)
    _logger = attr.ib(init=False, default=None, repr=False)

    @nom_court.default
    def _defaut_nom_court(self):
        """Dérive le nom court du script depuis ``nom`` (sans ``.py``)."""
        return re.sub(r"\.py$", "", os.path.basename(self.nom))

    @property
    def logger(self):
        """Loggeur pour le script_automatheque.

        Permet de charger par défaut la configuration du logger stockée dans
        le fichier de configuration, et de logger certaines actions de l'objet
        :class:`ScriptAutomatheque` (alors ces logs sont écrits en utilisant
        la configuration de `nom_du_script.main`)

        L'ideal est ensuite de gérer les loggers avec `logging.getLogger()`
        même si self.logger est quand même accessible dans la fonction wrappée.

        Si le logger pour le script n'a pas été déclaré, alors on utilise le
        logger automatheque.
        """
        if not self._logger:
            if not logger_existe(self.nom_court):
                self._logger = logging.getLogger("automatheque")
                self._logger.warning("Aucun logger pour '{}'.".format(self.nom_court))
                self._logger.warning("Utilisation du logger automatheque par défault.")
            else:
                self._logger = logging.getLogger(self.nom_court)
        return self._logger

    def joli_titre(self):
        self.logger.info("********** {} {} *********".format(self.nom, self.version))

    def initialise(self):
        # Un script EST une application : c'est le bon endroit pour activer le
        # logging console par défaut (la lib, elle, ne configure rien à l'import).
        configure_logging_defaut()
        # ``argv`` explicite (usage module/test) ou ``sys.argv`` par défaut
        # (``argv=None`` → docopt lit ``sys.argv[1:]``). Cf. #24.
        self.arguments = docopt.docopt(
            self.chaine_docopt, argv=self.argv, version=self.version
        )
        # Configuration en couches, de la plus générale à la plus spécifique
        # (chaque couche surcharge la précédente) :
        #   1. config.ini partagé d'automatheque  (chargé par ecraser=True)
        #   2. <racine>/<nom_court>/config.ini     (propre au script)
        #   3. --config <fichier>                  (explicite, ponctuel)
        fichiers = [
            os.path.join(
                constantes.repertoire_config_script(self.nom_court), "config.ini"
            )
        ]
        config_cli = self.arguments.get("--config")
        if config_cli:
            fichiers.append(config_cli)
        self.config = charge_configuration(fichiers, ecraser=True, recharger=True)
        # Commodités câblées automatiquement si le script les déclare dans son
        # usage docopt (sinon `.get` renvoie None → comportement par défaut).
        self.dry_run = bool(self.arguments.get("--dry-run"))
        self._applique_verbosite()
        # TODO(#27) ici on pourrait aussi merger la conf et les arguments ...
        # dans self.parametres ?
        """
        def merge(dict_1, dict_2):
            ""Merge two dictionaries.
            Values that evaluate to true take priority over falsy values.
            `dict_1` takes priority over `dict_2`.
            ""
            return dict((str(key), dict_1.get(key) or dict_2.get(key))
        for key in set(dict_2) | set(dict_1))
        """

    def execute_commande(self, registry=None):
        """Aiguille vers la commande commandopt correspondant aux arguments.

        Les commandes sont déclarées avec ``@commande([...])`` (alias de
        :func:`commandopt.commandopt`) ; ``execute_commande`` sélectionne celle
        dont les options obligatoires sont présentes dans ``self.arguments`` et
        l'exécute, en lui passant le dict d'arguments complet.

        Les :data:`OPTIONS_INTERNES` d'automatheque (``--config``, ``-v``…) sont
        **exclues de la sélection** : elles paramètrent le script sans le router.

        :param registry: :class:`commandopt.Registry` à interroger ; par défaut
            le registre global (façade :class:`commandopt.Command`).
        :raises commandopt.NoCommandFoundError: si aucune commande ne correspond.
        """
        cible = Command if registry is None else registry
        return cible.run(self.arguments, ignore=OPTIONS_INTERNES)

    def _niveau_journal_demande(self):
        """Traduit ``-v``/``-vv``/``-q`` en niveau de log, ou ``None``.

        ``None`` = ne rien changer (on garde le niveau INFO par défaut).
        ``--quiet``/``-q`` masque les INFO (WARNING) ; ``--verbose``/``-v``
        (répétable) descend en DEBUG.
        """
        args = self.arguments or {}
        if args.get("--quiet") or args.get("-q"):
            return logging.WARNING
        v = args.get("--verbose")
        if v is None:
            v = args.get("-v")
        try:
            v = int(v or 0)
        except (TypeError, ValueError):
            v = 1 if v else 0
        if v >= 1:
            return logging.DEBUG
        return None

    def _applique_verbosite(self):
        """Aligne le niveau de la **racine** sur ``-v``/``-q``.

        Le handler par défaut est posé sur la racine sans niveau (NOTSET, cf.
        ``constantes.logger_config_dict``) : il suffit d'ajuster le niveau du
        logger racine pour laisser passer plus (ou moins) de messages.
        """
        niveau = self._niveau_journal_demande()
        if niveau is None:
            return
        logging.getLogger().setLevel(niveau)

    def signale_debut_traitement(self):
        """Signale que le traitement a debuté.

        On pourrait aussi initialiser un logger et s'en servir.
        """
        self._debut = datetime.datetime.now()
        self.logger.info(
            "{}|{}| Début du traitement".format(
                self.nom, self._debut.strftime("%Y-%m-%d %H:%M:%S")
            )
        )

    def signale_fin_traitement(self):
        """Signale que le traitement est terminé (avec la durée si connue)."""
        fin = datetime.datetime.now()
        if self._debut is not None:
            duree = "{:.3f}s".format((fin - self._debut).total_seconds())
        else:
            duree = "?"
        self.logger.info(
            "{}|{}| Fin du traitement (durée : {})".format(
                self.nom, fin.strftime("%Y-%m-%d %H:%M:%S"), duree
            )
        )


# Alias court : `@script(...)` se lit mieux que `@script_automatheque(...)`.
# Le nom canonique reste disponible (rétrocompatibilité).
script = script_automatheque
