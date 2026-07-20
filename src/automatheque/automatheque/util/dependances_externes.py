"""Module d'aide à la gestion des dépendances externes.

Il est notamment utilisé :
* dans le package "dependance", qui sert à livrer des dépendances complètes avec
  automatheque (comme pour pyexiftool) et/ou à vérifier leur installation
  localement (en attendant peut être l'utilisation de poetry ou autre ?).
* dans des scripts qui utilisent automatheque, pour les aider à vérifier la
  présence de dépendances externes

# Fonctionnement :

Ce module fournit un registre des dépendances chargées.

Lorsqu'une dépendance est chargée, une instance de la classe Executant est créée,
et stockée dans le registre.

Ainsi c'est ce registre qu'il faut appeler si on a besoin d'une dépendance.

Il est ensuite conseillé de créer ses propres classes "wrapper" et de leur donner
l'instance de l'exécutant en paramètre, qui se chargera de faire les appels subprocess.

"""

import logging
import os
import shutil
import subprocess
from collections import namedtuple

import attr

from automatheque.exceptions import DependanceManquante

LOGGER = logging.getLogger(__name__)


MAUVAISE_CLE_ERREUR = """Aucune dépendance à ce nom n'a été trouvée.
Vérifiez que vous avez bien chargé la dépendance précédemment."""
registre_dependances: dict = {}
Dependance = namedtuple("Dependance", ["erreur", "presente", "executant"])


def verifie_dependance(cle_dependance):
    """Vérifie que la dépendance externe donnée est bien chargée.

    Renvoie une erreur si la dépendance n'est pas chargée ou que l'exécutable n'est
    pas présent, et ne renvoie rien sinon.

    :returns: None
    """
    try:
        d = registre_dependances[cle_dependance]
        if not d.presente:
            raise DependanceManquante(cle_dependance, d.erreur)
    except KeyError:
        raise DependanceManquante(cle_dependance, MAUVAISE_CLE_ERREUR)


def charge_dependance(
    cle,
    executable,
    executable_complet,
    erreur="",
    verifie=True,
    teste_execution=False,
):
    """Charge la dépendance donnée, dans le registre.

    :param teste_execution: si vrai, ne se contente pas de vérifier la présence
        de l'exécutable mais tente réellement de le lancer (cf.
        ``recup_executable``). Désactivé par défaut pour ne pas exécuter de
        binaire à l'insu de l'appelant.
    """
    executable = recup_executable(
        executable, executable_complet, teste_execution=teste_execution
    )
    executant = Executant(executable)

    # Ajout dans le registre des dépendances :
    d = {
        "erreur": erreur if erreur else _gen_erreur(cle),
        "presente": executable,
        "executant": executant,
    }
    registre_dependances[cle] = Dependance(**d)

    # On verifie que la dépendance existe et est bien chargée :
    if verifie:
        verifie_dependance(cle)

    # Si on arrive là alors la dépendance est bien vérifiée, on retourne "executant"
    return executant


def recup_executable(nom, chemin_complet, teste_execution=False):
    """Récupère le chemin vers l'exécutable demandé.

    :param teste_execution: si vrai, on ne se contente pas de vérifier que le
        fichier existe et porte le bit exécutable : on tente réellement de le
        lancer (cf. ``_executable_fonctionne``) pour détecter un binaire
        présent mais inutilisable (mauvaise architecture, interpréteur ou
        bibliothèque manquante…).
    :returns: str ou False
    """
    path = shutil.which(nom)
    # Si on ne trouve pas l'exécutable on essaie de forcer un chemin classique :
    if path is None:
        path = chemin_complet
        if not os.path.isfile(path) or not os.access(path, os.X_OK):
            return False
    if teste_execution and not _executable_fonctionne(path):
        return False
    return path


def _executable_fonctionne(path, timeout=2):
    """Vérifie qu'un exécutable démarre réellement (au-delà du bit exécutable).

    On le lance sans argument, entrées/sorties neutralisées, avec un délai
    court. Le **code de retour est ignoré** : de nombreux outils quittent en
    erreur sans argument (affichage de l'usage). Seul compte le fait que le
    système ait pu *démarrer* le binaire.

    * démarrage impossible (``OSError`` : « Exec format error », interpréteur
      manquant…) → ``False`` ;
    * délai dépassé → considéré comme fonctionnel (le binaire tournait bien) ;
    * démarrage OK (quel que soit le code de retour) → ``True``.
    """
    try:
        subprocess.run(
            [path],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return True
    except OSError:
        return False
    return True


def _gen_erreur(cle):
    """Génère une erreur standard pour la dépendance donnée."""
    return "\n{} n'est pas installé !\n".format(cle.title()).lstrip()


@attr.s
class Executant(object):
    """Classe pour faciliter l'exécution des dépendances."""

    executable = attr.ib()

    def exec(
        self,
        *args,
        stdin=None,
        cwd=None,
        env=None,
        timeout=None,
        check=False,
        text=False,
        encoding=None,
        **kwargs,
    ) -> subprocess.CompletedProcess:
        """Execute l'exécutable de la dépendance.

        Renvoie un `CompletedProcess
        <https://docs.python.org/3/library/subprocess.html#subprocess.CompletedProcess>`_.
        ``stdout`` et ``stderr`` sont **toujours capturés** (``PIPE``).

        Arguments de la ligne de commande :

        * les positionnels ``args`` sont ajoutés tels quels ;
        * les ``**kwargs`` sont ajoutés par **paires clé/valeur** :
          ``exec("build", mode="rapide")`` → ``[exe, "build", "mode", "rapide"]``.

        Options ``subprocess`` (paramètres nommés **réservés** : ces noms ne
        peuvent donc plus servir d'option CLI via ``kwargs``) :

        :param stdin:    entrée standard (objet fichier, ``PIPE``, ``DEVNULL``…).
            Défaut ``None`` = **héritée** du parent (auparavant un ``PIPE`` ouvert
            jamais alimenté, source de blocage). Cf. #66.
        :param cwd:      répertoire de travail du sous-processus.
        :param env:      environnement (dict) du sous-processus.
        :param timeout:  délai max en secondes ; à l'expiration, ``subprocess``
            tue le processus et lève ``subprocess.TimeoutExpired`` (propagé).
        :param check:    si vrai, lève ``CalledProcessError`` sur code non nul.
        :param text:     si vrai, ``stdout``/``stderr`` sont décodés en ``str``
            (défaut ``False`` = ``bytes``, comportement historique).
        :param encoding: encodage utilisé quand ``text`` (ou ``encoding``) est
            fourni.
        """
        procargs = [self.executable, *args]
        for k, v in kwargs.items():
            procargs += [k, v]

        msg_redir = " < 'stdin'" if stdin is not None else ""
        LOGGER.debug("Executant.exec : procargs=%s%s", procargs, msg_redir)
        return subprocess.run(
            procargs,
            stdin=stdin,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=cwd,
            env=env,
            timeout=timeout,
            check=check,
            text=text,
            encoding=encoding,
        )
