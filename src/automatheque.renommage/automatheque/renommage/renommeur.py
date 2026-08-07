# -*- coding: utf-8 -*-
"""Renommage et rangement de fichiers par gabarits.

Un **gabarit** est un squelette de chemin — `{date:%Y}/{album}/{nom}` — assorti
d'une condition qui dit quand il s'applique et d'un ordre qui le priorise. Le
**renommeur** choisit le premier gabarit applicable, en déduit un nouveau
chemin, et y déplace le fichier.

C'est l'opération symétrique de `automatheque.decomposition` : là où celle-ci
tire des métadonnées d'un chemin, celle-ci construit un chemin à partir de
métadonnées.
"""

import ast
import errno
import logging
import os
import shutil
from operator import attrgetter
from pathlib import Path
from typing import Iterator, List, Optional

import attr

from .condition import evalue_condition
from .exceptions import (
    AucunGabaritApplicable,
    GabaritInapplicable,
    TransfertIncomplet,
)

LOGGER = logging.getLogger(__name__)

# Section de configuration lue par défaut par `Gabarits.depuis_configuration`.
SECTION_CONFIG_PAR_DEFAUT = "renommage"


@attr.s
class Gabarit:
    """Gabarit à appliquer sur les objets `Renommable`.

    Un gabarit consiste en :

    * un **squelette** qui sera utilisé pour formatter l'objet `Renommable` à
      partir de ses champs disponibles et en déduire un nouveau nom ;
    * une **condition** qui détermine si le squelette est applicable ; un
      gabarit sans condition s'applique toujours ;
    * un **ordre** de traitement pour prioriser certains gabarits, le plus
      petit d'abord.
    """

    squelette: str = attr.ib(default="")
    condition: str = attr.ib(default="")
    ordre: int = attr.ib(default=0)


class Gabarits:
    """La liste des gabarits utilisables pour un renommage."""

    def __init__(self, gabarits: Optional[List[Gabarit]] = None):
        """Initialisation."""
        self._gabarits: List[Gabarit] = list(gabarits or [])
        self.gabarit_choisi: Optional[Gabarit] = None

    def __iter__(self) -> Iterator[Gabarit]:
        """Itère sur les gabarits, dans l'ordre où ils ont été ajoutés."""
        return iter(self._gabarits)

    def __len__(self) -> int:
        """Nombre de gabarits."""
        return len(self._gabarits)

    def __json__(self):
        """Pour pouvoir afficher les objets en JSON."""
        return [attr.asdict(g) for g in self._gabarits]

    def append(self, gabarit: Gabarit) -> None:
        """Ajoute un gabarit à la liste."""
        self._gabarits.append(gabarit)

    @classmethod
    def depuis_configuration(
        cls, config, section: str = SECTION_CONFIG_PAR_DEFAUT
    ) -> "Gabarits":
        """Construit les gabarits depuis une configuration de type `ConfigParser`.

        Chaque option de la section porte un triplet
        `[squelette, condition, ordre]`, écrit comme un littéral Python :

        ```ini
        [renommage]
        r1 = ['{date:%%Y}/{album}/{nom}', '"{album}"', 1]
        r2 = ['a-trier/{nom}', '', 9]
        ```

        Le triplet est lu avec `ast.literal_eval` et non `eval` : un fichier de
        configuration décrit des données, il n'a pas à pouvoir exécuter du code.

        :param config: objet exposant `options(section)` et `get(section, option)`
        :param section: section à lire
        :raise ValueError: si une option n'est pas un triplet lisible
        """
        gabarits = cls()
        for option in config.options(section):
            brut = config.get(section, option)
            try:
                squelette, condition, ordre = ast.literal_eval(brut)
            except (ValueError, SyntaxError) as exc:
                raise ValueError(
                    "[{}] {} : attendu [squelette, condition, ordre], lu {!r}".format(
                        section, option, brut
                    )
                ) from exc
            gabarits.append(
                Gabarit(squelette=squelette, condition=condition, ordre=ordre)
            )
        return gabarits

    def gabarits_valides(self, obj) -> Iterator[Gabarit]:
        """Génère les gabarits applicables à l'objet, dans l'ordre.

        D'abord ceux dont la condition est vérifiée, puis ceux qui n'ont pas de
        condition — les uns comme les autres classés par `ordre`. Un gabarit
        sans condition est donc un filet de sécurité, pas un concurrent.
        """
        avec_condition = [g for g in self._gabarits if g.condition]
        for gabarit in sorted(avec_condition, key=attrgetter("ordre")):
            if self.teste_condition(obj, gabarit.condition):
                yield gabarit

        sans_condition = [g for g in self._gabarits if not g.condition]
        for gabarit in sorted(sans_condition, key=attrgetter("ordre")):
            yield gabarit

    def choisit_gabarit(self, obj) -> Gabarit:
        """Retient le premier gabarit applicable, et le renvoie.

        :raise AucunGabaritApplicable: si aucun ne convient
        """
        try:
            self.gabarit_choisi = next(self.gabarits_valides(obj))
        except StopIteration:
            raise AucunGabaritApplicable()
        return self.gabarit_choisi

    @classmethod
    def teste_condition(cls, obj, condition: str) -> bool:
        """Teste la condition d'un gabarit sur l'objet donné.

        La condition est formatée avec les champs de l'objet, puis évaluée —
        `'"{album}" == "Meteora"'` avec les mêmes champs que le squelette.

        Une condition qui ne s'évalue pas — champ absent, expression mal
        formée — est **fausse**, pas fatale : le gabarit suivant est essayé.
        """
        try:
            formatee = condition.format(**obj._liste_champs_dispo())
            return bool(evalue_condition(formatee))
        except Exception:
            LOGGER.exception("Erreur durant le test de la condition.")
            return False


@attr.s
class Renommable:
    """Classe à hériter/surcharger pour être facilement renommable.

    L'objet doit exposer `filename`, le chemin du fichier à déplacer, et
    surcharger les deux méthodes ci-dessous.

    TODO : `filename` fait doublon avec `source` de `automatheque.schema.media`
    quand les deux sont mêlées par sous-classage — les deux noms désignent le
    même fichier et peuvent diverger après un renommage. À arbitrer.
    """

    filename: str = attr.ib(default="")  # TODO nom_fichier au lieu de filename

    @classmethod
    def _gabarits_par_defaut(cls) -> Gabarits:
        """Renvoie les gabarits à utiliser faute de mieux. À surcharger."""
        raise NotImplementedError

    def _liste_champs_dispo(self) -> dict:
        """Champs disponibles pour formater squelettes et conditions.

        À surcharger : c'est la projection des métadonnées de l'objet vers le
        vocabulaire des gabarits, et elle est propre à chaque application.

        TODO : on peut même gérer plusieurs langues !
        """
        raise NotImplementedError

    def renomme(self, rep_cible, gabarits=None, debug=False, force=False, copier=False):
        """Enveloppe de `Renommeur.renomme` pour le cas courant."""
        return Renommeur(self, gabarits=gabarits).renomme(
            rep_cible, debug=debug, force=force, copier=copier
        )


class Renommeur:
    """Gère le renommage de l'objet `Renommable` donné.

    Le renommage est effectué à partir de gabarits spécifiques, que l'on peut
    écrire soi-même.
    """

    def __init__(self, obj: Renommable, gabarits: Optional[Gabarits] = None):
        """Initialisation.

        La configuration n'est plus **cherchée** ici : elle est **reçue**. Un
        appelant qui range ses gabarits dans un fichier de configuration les
        construit avec `Gabarits.depuis_configuration(config, section)` et les
        passe ici. Le renommeur, lui, ne consulte aucun état global — ce qui le
        rend testable et prévisible.

        :param obj: doit être un objet `Renommable`
        :param gabarits: gabarits à appliquer ; à défaut, ceux que l'objet
                         renvoie par `_gabarits_par_defaut()`
        """
        if not isinstance(obj, Renommable):
            raise ValueError("obj doit etre une instance de Renommable")
        self.obj = obj
        self.gabarits = gabarits if gabarits is not None else obj._gabarits_par_defaut()

    def _construire_nouveau_nom(self) -> str:
        """Construit le nouveau nom de l'objet à renommer.

        :raise AucunGabaritApplicable: si aucun gabarit ne convient
        :raise GabaritInapplicable: si le squelette retenu ne peut être formaté
        """
        champs = self.obj._liste_champs_dispo()
        gabarit = self.gabarits.choisit_gabarit(self.obj)
        LOGGER.debug("Gabarit choisi : %s", gabarit)
        try:
            return gabarit.squelette.format(**champs)
        except (KeyError, IndexError, ValueError, AttributeError, TypeError) as exc:
            raise GabaritInapplicable(gabarit.squelette, str(exc)) from exc

    def _renomme(self, rep_cible, nom_fichier, debug=False, force=False, copier=False):
        """Déplace le fichier vers `rep_cible/nom_fichier`.

        Le transfert est une copie suivie d'une vérification de taille, puis de
        la suppression de l'original — `shutil.move` ne dirait pas si la copie
        s'est mal passée entre deux systèmes de fichiers.

        :returns: le chemin cible, qu'il ait été atteint ou non
        """
        fichier_cible = os.path.join(rep_cible, nom_fichier)
        fichier_orig = self.obj.filename

        if debug or (os.path.exists(fichier_cible) and not force):
            LOGGER.warning(
                "Pas de deplacement : %s", "debug" if debug else "fichier existe"
            )
            return fichier_cible

        # Creation du répertoire parent si besoin :
        Path(os.path.dirname(fichier_cible)).mkdir(parents=True, exist_ok=True)

        LOGGER.debug("Déplacement vers cible : %s", fichier_cible)
        try:
            # Attention, si le fichier cible existe il est écrasé.
            # Pour changer ce fonctionnement voir ici :
            # https://gist.github.com/alexwlchan/c2adbb8ee782f460e5ec
            shutil.copy(fichier_orig, fichier_cible)
        except OSError as exc:
            if exc.errno != errno.ENOTSUP:
                LOGGER.error(
                    "[E] Echec shutil.copy(%s, %s) : %s",
                    fichier_orig,
                    fichier_cible,
                    exc,
                )
                raise
            # ENOTSUP remonte lorsque l'on ne peut pas changer les droits ou
            # les attributs d'un fichier. Le transfert s'est peut-être bien
            # passé malgré tout : on le vérifie juste après.

        if os.path.getsize(fichier_cible) != os.path.getsize(fichier_orig):
            raise TransfertIncomplet(fichier_orig, fichier_cible)

        # La cible est bonne : c'est seulement maintenant que l'objet déménage.
        self.obj.filename = fichier_cible
        if not copier:
            os.remove(fichier_orig)
        return fichier_cible

    def renomme(self, rep_cible, debug=False, force=False, copier=False):
        """Range le fichier dans `rep_cible`, sous le nom que dictent les gabarits.

        :param rep_cible: répertoire cible du déplacement
        :param debug: calcule le chemin cible sans rien déplacer
        :param force: écrase un fichier cible existant
        :param copier: conserve l'original au lieu de le supprimer
        :returns: le chemin cible
        """
        nom_fichier = self._construire_nouveau_nom()
        return self._renomme(
            rep_cible, nom_fichier, debug=debug, force=force, copier=copier
        )
