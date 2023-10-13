# -*- coding:utf-8 -*-
"""Utilitaire pour faciliter la création de scripts basés sur automatheque.

TODO cookiecutter : ? https://github.com/LucasRGoes/ports-adapters-sample/blob/master/app/settings.py

Il faut pouvoir l'utiliser aussi dans les modules, pas juste dans les scripts.
TODO !!

Le format que l'on souhaite est le suivant :
```
'''Mon script

Usage:
  mon_script.py [--action] [--config=<fichier_config>]

Options:
  --action  Action realisée
  --config=<fichier_config>  Fichier de configuration [default: mon_script.ini]
'''
__version__ = '0.1a'  # ou importer depuis mon_package.__version__

@script_automatheque(__doc__, __version__)
def main(..., _script=None):
    # code à exécuter
    # _script est un objet `ScriptAutomatheque`
    print(_script)

if __name__ == '__main__':
    main(...)
```
Cela déclenche les logs de début, de fin, parse les arguments etc.
"""

import sys
import os
import re
import datetime
from functools import wraps

import docopt

from automatheque.configuration import charge_configuration, NoOptionError
from automatheque.log import recup_logger, logger_existe


def script_automatheque(chaine_docopt, version=None):
    """Decorateur pour ScriptAutomatheque.

    - signale le début et la fin du traitement
    - passe un objet ScriptAutomatheque à la fonction appelante
    """
    s = ScriptAutomatheque(
        nom=sys.argv[0], chaine_docopt=chaine_docopt, version=version
    )
    s.initialise()

    def decorateur(fonction):
        @wraps(fonction)
        def init_script(*args, **kwds):
            try:
                s.joli_titre()
                s.signale_debut_traitement()
                return fonction(_script=s, *args, **kwds)
            finally:
                s.signale_fin_traitement()

        return init_script

    return decorateur


class ScriptAutomatheque(object):
    """Objet ScriptAutomatheque qui automatise la creation de scripts.

    Cet objet contient :
    - self.arguments : les arguments récupérés par docopt
    - self.config : automatiquement extraite de l'argument --config si présent
                    mergée avec la configuration d'automatheque
    - self.parametres : merge de arguments avec config
    - self.logger : logger pour les appels internes de ScriptAutomatheque

    """

    def __init__(self, nom, chaine_docopt, version=None):
        self.nom = nom
        self.nom_court = re.sub(r"\.py$", "", os.path.basename(nom))
        self.chaine_docopt = chaine_docopt
        self.version = version
        self.arguments = None
        self.config = None
        self._logger = None

    def __repr__(self):
        """TODO utiliser attrs."""
        return "<ScriptAutomatheque {} {} {}>".format(
            self.nom, self.arguments, self.config
        )

    @property
    def logger(self):
        """Loggeur pour le script_automatheque.

        Permet de charger par défaut la configuration du logger stockée dans
        le fichier de configuration, et de logger certaines actions de l'objet
        :class:`ScriptAutomatheque` (alors ces logs sont écrits en utilisant
        la configuration de `nom_du_script.main`)

        L'ideal est ensuite de gérer les loggers avec `logging.getLogger()` ou
        son wrapper `automatheque.log.recup_logger()` même si self.logger est
        quand même accessible dans la fonction wrappée.

        Si le logger pour le script n'a pas été déclaré, alors on utilise le
        logger automatheque.
        """
        if not self._logger:
            if not logger_existe(self.nom_court):
                self._logger = recup_logger()
                self._logger.warning("Aucun logger pour '{}'.".format(self.nom_court))
                self._logger.warning("Utilisation du logger automatheque par défault.")
            else:
                self._logger = recup_logger(self.nom_court)
        return self._logger

    def joli_titre(self):
        self.logger.info("********** {} {} *********".format(self.nom, self.version))

    def initialise(self):
        self.arguments = docopt.docopt(self.chaine_docopt, version=self.version)
        try:
            if self.arguments["--config"]:
                # On écrase les configurations précédentes (par ex si
                # automatheque a déjà été chargé) car on estime que
                # l'annotation vient avec des informations supplémentaires.
                self.config = charge_configuration(
                    [self.arguments["--config"]], ecraser=True, recharger=True
                )
            else:
                self.config = charge_configuration(ecraser=True, recharger=True)
        except KeyError:
            self.config = charge_configuration(ecraser=True, recharger=True)
        # TODO ici on pourrait aussi merger la conf et les arguments ...
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

    def signale_debut_traitement(self):
        """Signale que le traitement a debuté.

        On pourrait aussi initialiser un logger et s'en servir.
        """
        self.logger.info(
            "{}|{}| Début du traitement".format(
                self.nom, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%s")
            )
        )

    def signale_fin_traitement(self):
        """Signale que le traitement est terminé."""
        self.logger.info(
            "{}|{}| Fin du traitement".format(
                self.nom, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%s")
            )
        )
