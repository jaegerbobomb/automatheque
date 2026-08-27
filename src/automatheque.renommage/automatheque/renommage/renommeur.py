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
import re
import shutil
from operator import attrgetter
from pathlib import Path
from typing import Iterator, List, Optional

import attr

from automatheque.util.fichier import enleve_caracteres_invalides

from .condition import evalue_condition
from .exceptions import (
    AucunGabaritApplicable,
    CibleHorsRepertoire,
    ConditionInvalide,
    GabaritInapplicable,
    TransfertIncomplet,
)

LOGGER = logging.getLogger(__name__)

# Section de configuration lue par défaut par `Gabarits.depuis_configuration`.
SECTION_CONFIG_PAR_DEFAUT = "renommage"

# Valeurs de champ qui, laissées telles quelles, désignent un répertoire au
# lieu d'un nom : elles feraient remonter l'arborescence.
_SEGMENTS_RELATIFS = (".", "..")


def _assainit_champ(valeur):
    """Neutralise ce qu'une valeur de champ pourrait faire au chemin.

    Les champs d'un squelette viennent des **métadonnées des fichiers
    traités** — un album, une ville, un titre. Substitués tels quels, ils
    peuvent sortir du répertoire cible : `os.path.join` jette son premier
    argument dès que le second est absolu, et `..` remonte d'un niveau.

    Seules les chaînes sont assainies. Les autres valeurs — dates, nombres,
    objets — passent intactes, sans quoi les spécificateurs de format des
    squelettes (`{date:%Y}`) cesseraient de fonctionner ; elles n'ont de toute
    façon pas de séparateur à porter avant leur propre formatage.

    Les séparateurs présents dans le **squelette**, eux, sont conservés :
    c'est par eux que l'auteur du gabarit décrit son arborescence.
    """
    if not isinstance(valeur, str):
        return valeur
    valeur = enleve_caracteres_invalides(valeur)
    if valeur.strip() in _SEGMENTS_RELATIFS:
        return "_" * len(valeur.strip())
    return valeur


def _cible_contenue(rep_cible, nom_fichier):
    """Renvoie le chemin cible, après avoir vérifié qu'il reste dans le répertoire.

    Deuxième ligne de défense, après l'assainissement des champs : un squelette
    absolu, ou une combinaison qu'on n'avait pas prévue, ne doit pas pouvoir
    écrire ailleurs que sous `rep_cible`.

    :raise CibleHorsRepertoire: si le chemin construit s'en échappe
    """
    racine = os.path.abspath(rep_cible)
    cible = os.path.abspath(os.path.join(racine, nom_fichier))
    if cible != racine and not cible.startswith(racine + os.sep):
        raise CibleHorsRepertoire(cible, racine)
    return cible


def _reserve(chemin, force=False):
    """Prend le nom cible, atomiquement, et dit si on l'a obtenu.

    ``os.open(..., O_CREAT | O_EXCL)`` est **la** primitive de mutuelle exclusion
    d'un système de fichiers : le noyau garantit qu'un seul appelant crée le
    fichier, tous les autres reçoivent ``EEXIST``. Le fichier est créé **vide** ;
    c'est lui qui tient la place jusqu'à ce que la copie le remplisse.

    Le ``os.path.exists()`` qu'elle remplace ne garantissait rien : entre le test
    et la copie, deux appelants concurrents se croyaient tous deux les premiers,
    écrivaient vers le même chemin, et **supprimaient tous deux leur original**
    — un fichier perdu, sans la moindre erreur journalisée.

    :param force: écraser une cible existante est déjà permis ; il n'y a alors
        rien à réserver, le nom est pris et on a l'autorisation de l'écraser
    :returns: ``True`` si le nom est à nous, ``False`` s'il était déjà pris
    """
    try:
        descripteur = os.open(chemin, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o666)
    except FileExistsError:
        return bool(force)
    os.close(descripteur)
    return True


def _efface(chemin):
    """Supprime un fichier sans se plaindre s'il n'est pas là."""
    try:
        os.remove(chemin)
    except FileNotFoundError:
        pass  # rien à effacer : la copie n'a rien écrit
    except OSError:  # pragma: no cover - dépend du système de fichiers
        LOGGER.warning("Impossible de supprimer la cible incomplète %s", chemin)


def _nom_relatif(nom_fichier: str, squelette_absolu: bool) -> str:
    """Réduit le nom formaté à un chemin propre, sans segment vide.

    Un champ de **tête** vide — `{annee}/{album}/{nom}` avec `annee=""` — laisse
    un séparateur en tête (`"/Japon/x.jpg"`) qui rend le chemin **absolu** :
    `os.path.join(rep_cible, …)` jette alors `rep_cible`, et le fichier
    quitterait le répertoire cible (rattrapé plus loin par `CibleHorsRepertoire`,
    mais pour rien — un champ manquant est bénin). On retire donc les segments
    vides (tête, queue, séparateurs doublés) : le champ manquant devient un
    segment sauté.

    En revanche, un squelette **écrit** absolu (`"/etc/{nom}"`) est une erreur
    d'auteur : on le laisse absolu pour que `_cible_contenue` le refuse. D'où le
    drapeau `squelette_absolu`, décidé sur le squelette et non sur son rendu —
    les deux sont indiscernables une fois formatés.
    """
    segments = [s for s in re.split(r"[/\\]+", nom_fichier) if s]
    if not segments:
        return nom_fichier
    chemin = os.path.join(*segments)
    if squelette_absolu:
        chemin = os.sep + chemin
    return chemin


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
            erreur = "[{}] {} : attendu [squelette, condition, ordre], lu {!r}".format(
                section, option, brut
            )
            try:
                triplet = ast.literal_eval(brut)
            except (ValueError, SyntaxError) as exc:
                raise ValueError(erreur) from exc
            # `literal_eval` accepte bien plus qu'un triplet : `5` (dépaquetage
            # `TypeError` obscur plus loin) ou surtout `'abc'` — une chaîne de 3
            # caractères se dépaquette en `('a', 'b', 'c')` et **passe**, pour ne
            # casser que dans un `sorted(key=…)` sans rapport. On exige donc
            # explicitement une séquence (hors chaîne) de trois éléments.
            if isinstance(triplet, (str, bytes)) or not isinstance(
                triplet, (list, tuple)
            ):
                raise ValueError(erreur)
            if len(triplet) != 3:
                raise ValueError(erreur)
            squelette, condition, ordre = triplet
            # Arité bonne, mais les types comptent aussi : un `ordre` non entier
            # (`['{nom}', '', '9']`) passe ici pour n'exploser qu'au
            # `sorted(key=ordre)` de `gabarits_valides`, en `TypeError` sans
            # rapport avec la configuration. On le refuse donc à la source.
            if not (
                isinstance(squelette, str)
                and isinstance(condition, str)
                and isinstance(ordre, int)
                and not isinstance(ordre, bool)
            ):
                raise ValueError(
                    erreur + " (squelette et condition en chaîne, ordre entier)"
                )
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

        Le catch est **restreint** aux erreurs de *formatage* et d'*évaluation*
        de la condition. Un bug réel du `_liste_champs_dispo()` du consommateur
        (typo, `NotImplementedError`) doit remonter, pas se déguiser en
        « condition fausse » ; on l'appelle donc **hors** du `try`.
        """
        champs = obj._liste_champs_dispo()
        try:
            formatee = condition.format(**champs)
            return bool(evalue_condition(formatee))
        except (
            KeyError,
            IndexError,
            AttributeError,
            ValueError,
            TypeError,
            ConditionInvalide,
        ):
            LOGGER.debug("Condition écartée (non évaluable) : %s", condition)
            return False


@attr.s
class Renommable:
    """Classe à hériter/surcharger pour être facilement renommable.

    L'objet doit **exposer un attribut `source`** — le chemin du fichier à
    déplacer — et surcharger les deux méthodes ci-dessous. `Renommable` ne
    déclare pas `source` lui-même : c'est le consommateur qui le fournit (par
    exemple `automatheque.schema.media.Media`, dont c'est déjà l'attribut). Le
    renommage lit et **écrit** dans `source` : après un rangement, `source`
    pointe la cible, et tout ce qui en dérive (nom de base, extension…) suit.

    C'est une **convention** — un nom d'attribut attendu — sans dépendance vers
    `schema`, comme le contrat de `automatheque.decomposition`. On évite ainsi
    deux vérités pour un même fichier (l'ancien `filename` propre à `Renommable`
    divergeait de `source` après un renommage).
    """

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
        champs = {
            cle: _assainit_champ(valeur)
            for cle, valeur in self.obj._liste_champs_dispo().items()
        }
        gabarit = self.gabarits.choisit_gabarit(self.obj)
        LOGGER.debug("Gabarit choisi : %s", gabarit)
        try:
            nom = gabarit.squelette.format(**champs)
        except (KeyError, IndexError, ValueError, AttributeError, TypeError) as exc:
            raise GabaritInapplicable(gabarit.squelette, str(exc)) from exc
        # `squelette_absolu` est décidé sur le squelette, pas sur son rendu : un
        # champ de tête vide (`{annee}/…` avec `annee=""`) rend `nom` absolu par
        # accident et le ferait quitter rep_cible — on rabote alors les segments
        # vides ; un squelette **écrit** absolu (`/etc/{nom}`) reste absolu pour
        # que `_cible_contenue` le refuse.
        squelette_absolu = gabarit.squelette.startswith(("/", os.sep))
        return _nom_relatif(nom, squelette_absolu)

    def _renomme(self, rep_cible, nom_fichier, debug=False, force=False, copier=False):
        """Déplace le fichier vers `rep_cible/nom_fichier`.

        Le transfert est une copie suivie d'une vérification de taille, puis de
        la suppression de l'original — `shutil.move` ne dirait pas si la copie
        s'est mal passée entre deux systèmes de fichiers.

        Le nom cible est **réservé** avant la copie (`_reserve`) : c'est ce qui
        rend l'opération sûre quand plusieurs processus rangent en parallèle.
        Seule la réservation est sérialisée — un appel système ; les copies,
        elles, restent simultanées.

        :raise CibleHorsRepertoire: si le chemin construit sort de `rep_cible`
        :returns: le chemin cible, qu'il ait été atteint ou non
        """
        fichier_cible = _cible_contenue(rep_cible, nom_fichier)
        fichier_orig = self.obj.source
        if not fichier_orig:
            # Refus explicite : sans `source`, il n'y a rien à déplacer. Mieux
            # vaut le dire ici qu'un `shutil.copy(None, …)` obscur au fond de la
            # pile (l'ancien défaut `filename=""` donnait le même genre d'échec
            # tardif). Cf. #117.
            raise ValueError(
                "Renommable sans `source` : rien à déplacer. L'objet doit "
                "exposer le chemin du fichier dans son attribut `source`."
            )

        if debug:
            LOGGER.warning("Pas de deplacement : debug")
            return fichier_cible

        # Creation du répertoire parent si besoin (avant la réservation :
        # `O_CREAT` a besoin d'un répertoire qui existe pour aboutir).
        Path(os.path.dirname(fichier_cible)).mkdir(parents=True, exist_ok=True)

        if not _reserve(fichier_cible, force):
            LOGGER.warning("Pas de deplacement : fichier existe")
            return fichier_cible

        LOGGER.debug("Déplacement vers cible : %s", fichier_cible)
        # Tout ce qui suit écrit dans une cible dont **on** est responsable : le
        # moindre échec la reprend (`_efface`), sans quoi la place resterait
        # tenue par un fichier vide ou tronqué que le prochain essai prendrait
        # pour un succès. L'original, lui, n'est jamais touché avant la
        # vérification de taille.
        try:
            try:
                # La cible est à nous : elle est vide, `shutil.copy` la remplit
                # (ou écrase la cible existante quand `force`).
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

            if not os.path.exists(fichier_cible) or os.path.getsize(
                fichier_cible
            ) != os.path.getsize(fichier_orig):
                raise TransfertIncomplet(fichier_orig, fichier_cible)
        except BaseException:
            _efface(fichier_cible)
            raise

        # La cible est bonne : c'est seulement maintenant que l'objet déménage.
        # On écrit dans `source` — le seul porteur de vérité du chemin : nom de
        # base, extension, étiquettes rechargées… tout en dérive et suit.
        self.obj.source = fichier_cible
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
