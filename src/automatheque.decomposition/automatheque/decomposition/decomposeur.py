# -*- coding: utf-8 -*-
"""Décomposition de chaînes et d'arborescences par patrons.

La décomposition consiste à extraire des informations d'une chaîne — le plus
souvent le chemin d'un fichier — en lui appliquant une série d'expressions
rationnelles, puis à reverser le résultat dans un objet.

Le module ne touche pas au système de fichiers : il ne manipule que des
chaînes. Un chemin lui est donné, il en tire des informations ; c'est
l'appelant qui décide ensuite quoi en faire.
"""

import logging
import pickle
import re
from copy import deepcopy

import attr

from automatheque.exceptions import ArgumentManquant
from automatheque.util.repertoire import remonte_arborescence

from .exceptions import DecompositionEchecPatron, DecompositionEchecTousPatrons

LOGGER = logging.getLogger(__name__)

#
# Constantes pour déterminer le comportement de la décomposition.
#
# Le premier résultat non nul de la décomposition est renvoyé :
DECOMPOSE_RESULTAT_PREMIER_NON_NUL = "resultat_premier_non_nul"
# Tous les résultats trouvés par les decomposeurs sont renvoyés :
DECOMPOSE_RESULTAT_CUMULE = "resultat_cumule"
# On renvoie le resultat avec la taille de l'objet maximale :
DECOMPOSE_RESULTAT_MAX_INFOS = "resultat_max_infos"

#
# Détermine si on modifie la chaîne à analyser et si on relance une analyse :
#
# Seul un niveau d'analyse est joué (généralement le nom de l'objet):
DECOMPOSE_ANALYSE_ARBO_UN_NIVEAU = "analyse_un_niveau"
# Tous les niveaux de l'arborescence sont analysés, un par un :
DECOMPOSE_ANALYSE_ARBO_COMPLETE = "analyse_arbo_complete"
# Tous les niveaux de l'arborescence sont concaténés pour former la chaîne à
# analyser, ex: /media/series/ma serie S01/E02.avi => ma_serie_S01_E02.avi
# étant donné une "racine" (ici /media/series, ou par défaut "/").
# NB: cette analyse joue quand même les niveaux les uns après les autres :
# ie : d'abord analyse de E02.avi avant ma_serie_S01_E02.avi.
# Si on voulait analyser directement tout le chemin, il suffit de faire une
# analyse simple en mettant dès le départ la chaîne complète dans la source.
DECOMPOSE_ANALYSE_ARBO_CONCATENE = "analyse_arbo_concatene"


# Sentinelle : distingue « pas de résultat à renvoyer, continuer l'analyse » de
# « résultat trouvé, même **vide** » — une capture peut valoir `''`. Les
# confondre (un résultat vide vu comme *falsy*) faisait perdre une décomposition
# gagnante et poursuivre l'analyse sur les répertoires parents. Cf. #116.
_CONTINUER = object()


def _valeurs_champs(obj):
    """Valeurs des attributs de ``obj``, que sa classe soit à *slots* ou non.

    ``obj.__dict__`` n'existe pas sur une classe attrs à *slots* (`attrs.define`,
    le style moderne, et le défaut de la bibliothèque) : on passe alors par
    ``attr.asdict`` (sans récursion, pour rester au niveau des attributs comme le
    faisait ``__dict__``). Repli **explicite** sur ``[]`` plutôt qu'une
    ``AttributeError`` avalée qui faisait échouer toute la décomposition. Cf. #116.
    """
    if attr.has(type(obj)):
        return list(attr.asdict(obj, recurse=False).values())
    try:
        return list(vars(obj).values())
    except TypeError:
        return []


def _appel_source_par_defaut(obj, valeur):
    """Source de données par défaut : celle que l'objet décomposable prépare."""
    return obj._prepare_decomposition(valeur)


@attr.s
class Decomposeur(object):
    """Un patron de décomposition : une expression rationnelle et ses appels.

    Les fonctions servent :

    * pour obtenir la source des données (:attr:`appel_source`) ;
    * pour traiter les données récupérées (:attr:`appel_en_retour`).

    :param chaine: expression rationnelle appliquée à la source
    :param appel_en_retour: appelé en `(obj, resultats)` pour reverser dans
                            l'objet ce que le patron a trouvé
    :param appel_source: appelé en `(obj, valeur)` pour obtenir la chaîne à
                         analyser ; par défaut, délègue à
                         `obj._prepare_decomposition(valeur)`
    :param drapeaux: drapeaux passés à :func:`re.compile`
    :param poids: priorité du patron, utilisée par
                  :data:`DECOMPOSE_RESULTAT_MAX_INFOS`
    """

    chaine = attr.ib()
    appel_en_retour = attr.ib()
    appel_source = attr.ib(default=None)
    drapeaux = attr.ib(default=0)
    poids = attr.ib(default=1)
    compile = attr.ib(init=False, default=None)

    def __attrs_post_init__(self):
        """Complète les propriétés déduites des autres."""
        if self.appel_source is None:
            self.appel_source = _appel_source_par_defaut
        self.compile = re.compile(self.chaine, flags=self.drapeaux)

    def _decomposer(self, obj, valeur=None, pos=None, endpos=None):
        """Applique l'expression rationnelle sur la source des données.

        :param valeur: si une valeur est donnée elle est passée à la fonction
                       :attr:`appel_source` qui prépare les données à
                       décomposer.
        """
        # `pos is not None` et non `if pos` : 0 est une position valide (début de
        # chaîne), qu'un test de véracité écarterait. Et `endpos` fourni seul est
        # respecté au lieu d'être silencieusement jeté.
        kwargs = {}
        if pos is not None:
            kwargs["pos"] = pos
        if endpos is not None:
            kwargs["endpos"] = endpos

        return self.compile.findall(self.appel_source(obj, valeur), **kwargs)


@attr.s
class Decomposeurs(object):
    """Classe « abstraite » dont doivent hériter tous les jeux de patrons.

    TODO: rendre la classe vraiment abstraite !
    """

    decomposeurs = attr.ib(init=False, factory=list)

    def __iter__(self):
        """Itère sur les décomposeurs."""
        return iter(self.decomposeurs)


class Decomposable(object):
    """Les objets qui héritent de cette classe sont décomposables.

    Il faut alors appeler :meth:`decompose` (ou :meth:`auto_decompose`).

    L'objet doit exposer deux attributs, sur lesquels s'appuie la
    décomposition :

    * ``basename`` — la chaîne analysée par défaut ;
    * ``source`` — le chemin complet, remonté niveau par niveau par les
      options :data:`DECOMPOSE_ANALYSE_ARBO_COMPLETE` et
      :data:`DECOMPOSE_ANALYSE_ARBO_CONCATENE`.

    C'est une **convention** — un nom d'attribut attendu — sans dépendance vers
    `schema`. Le chemin est nommé ``source``, comme chez
    `automatheque.schema.media.Media` et `automatheque.renommage.Renommable` :
    un seul porteur de vérité du chemin pour tout le socle média, dont dérive
    aussi ``basename``. (Auparavant ``filename``, qui divergeait de
    ``Media.source`` ; cf. #117.)

    TODO : on pourrait donner le nom de la propriété à l'initialisation de
    Decomposable, si on veut en prendre une autre.
    """

    @classmethod
    def _decomposeurs_par_defaut(cls):
        """À surcharger par les descendants.

        Renvoie une instance de :class:`Decomposeurs` ou le chemin vers la
        classe.
        """
        raise NotImplementedError("pas de decomposeurs par défaut")

    def _prepare_decomposition(self, valeur=None):
        """Fonction par défaut pour récupérer la donnée à décomposer.

        À surcharger si on veut normaliser la donnée.
        Attention, si valeur est None, cette fonction doit renvoyer une donnée
        malgré tout.

        :param valeur:  valeur à préparer si présente, sinon basename par
                        défaut
        """
        if valeur:
            return valeur
        return self.basename

    def auto_decompose(self, racine=None, decomposeurs=None):
        """Essaie les combinaisons d'options jusqu'à ce que l'une réussisse.

        Les combinaisons sont parcourues de la plus riche à la plus simple.

        :raise DecompositionEchecTousPatrons: si aucune combinaison n'aboutit
        """
        for options_resultat in [
            DECOMPOSE_RESULTAT_MAX_INFOS,
            DECOMPOSE_RESULTAT_CUMULE,
            DECOMPOSE_RESULTAT_PREMIER_NON_NUL,
        ]:
            for option in [
                DECOMPOSE_ANALYSE_ARBO_COMPLETE,
                DECOMPOSE_ANALYSE_ARBO_CONCATENE,
            ]:
                try:
                    self.decompose(
                        decomposeurs=decomposeurs,
                        racine=racine,
                        options_analyse=option,
                        options_resultat=options_resultat,
                    )
                except DecompositionEchecTousPatrons:
                    pass
                else:
                    return
        raise DecompositionEchecTousPatrons()

    def decompose(
        self,
        decomposeurs=None,
        racine=None,
        options_resultat=DECOMPOSE_RESULTAT_PREMIER_NON_NUL,
        options_analyse=DECOMPOSE_ANALYSE_ARBO_UN_NIVEAU,
    ):
        """Décompose l'objet suivant les decomposeurs donnés."""
        identificateur = Identificateur(self, decomposeurs=decomposeurs)
        return identificateur.identifie(
            racine=racine,
            options_resultat=options_resultat,
            options_analyse=options_analyse,
        )


@attr.s
class Identificateur(object):
    """Identifie une chaîne grâce à une liste de décomposeurs.

    Identificateur = algo d'utilisation des décomposeurs. Il permet de prendre
    la décomposition la plus pertinente parmi celles que les patrons
    proposent.

    Utilisé en particulier pour déterminer le nom d'une série ou d'une chanson
    à partir de son nom de fichier.

    :param obj: l'objet que l'on veut identifier (un :class:`Decomposable`)
    :param decomposeurs: instance de :class:`Decomposeurs`, ou la chaîne
                         d'import correspondant à la classe, ex :
                         ``"mon_paquet.decomposeurs_serie.SerieSaisonDecomposeurs"``.
                         À défaut, ceux que l'objet renvoie par
                         ``_decomposeurs_par_defaut()``.

    TODO renommer DECOMPOSE_XX en IDENTIFIE_XXX
    TODO : attr utiliser validator et converter
    """

    obj = attr.ib()
    decomposeurs = attr.ib(default=None)

    def __attrs_post_init__(self):
        """Résout les décomposeurs et prend un témoin de l'objet d'origine."""
        if not self.decomposeurs:
            try:
                self.decomposeurs = self.obj._decomposeurs_par_defaut()
            except (AttributeError, NotImplementedError):
                # L'objet n'est pas décomposable, ou ne propose pas de patrons
                # par défaut : sans patron on ne peut rien identifier.
                raise ArgumentManquant("decomposeurs")

        if isinstance(self.decomposeurs, str):
            # Cas où le decomposeur est donné par son chemin :
            from pydoc import locate

            classe = locate(self.decomposeurs)
            if classe is None:
                raise ArgumentManquant("decomposeurs")
            self.decomposeurs = classe()

        # Pour comparer RESULTAT_MAX_INFOS il faut un objet témoin :
        self.obj_temoin = deepcopy(self.obj)

    def _exec_decomposition(self, options_resultat, valeur=None):
        """Joue tous les décomposeurs sur la valeur donnée.

        :return: tuple `(decomposition_reussie, sortir)` où `sortir` porte le
                 résultat à renvoyer immédiatement (y compris une chaîne vide),
                 ou la sentinelle `_CONTINUER` s'il faut poursuivre l'analyse.
        """
        decomposition_reussie = False
        sortir = _CONTINUER
        for decomposeur in self.decomposeurs:
            LOGGER.debug(
                "exec_decomposition : {} // {}".format(
                    decomposeur.chaine, valeur or self.obj.basename
                )
            )
            try:
                resultats = decomposeur._decomposer(self.obj, valeur)
                try:
                    resultats = resultats[0]
                except IndexError:
                    raise DecompositionEchecPatron(decomposeur)
                if options_resultat == DECOMPOSE_RESULTAT_PREMIER_NON_NUL:
                    # Puis on appelle le callback pour remplir l'objet :
                    decomposeur.appel_en_retour(self.obj, resultats)
                    decomposition_reussie = True
                    sortir = resultats
                    # on s'arrête ici
                    break
                elif options_resultat == DECOMPOSE_RESULTAT_CUMULE:
                    # Puis on appelle le callback pour remplir l'objet :
                    decomposeur.appel_en_retour(self.obj, resultats)
                    decomposition_reussie = True
                    # mais on continue le traitement :
                    continue
                elif options_resultat == DECOMPOSE_RESULTAT_MAX_INFOS:
                    obj_temoin = deepcopy(self.obj_temoin)
                    decomposeur.appel_en_retour(obj_temoin, resultats)

                    # On compare la taille des deux objets sérialisés, grosso
                    # modo. On n'attribue un modificateur qu'à l'objet témoin
                    # pour prendre en compte la « qualité » du décomposeur en
                    # cours.
                    temoin = self._score_max_infos(obj_temoin, decomposeur.poids)
                    if temoin >= self._score_max_infos(self.obj):
                        # Puis on appelle le callback pour remplir l'objet :
                        decomposeur.appel_en_retour(self.obj, resultats)
                        decomposition_reussie = True
                    # mais on continue le traitement :
                    continue
            except DecompositionEchecPatron:
                LOGGER.debug(
                    "Echec de la décomposition: {} {}".format(
                        valeur, decomposeur.chaine
                    )
                )
            except Exception:
                LOGGER.exception(
                    "Echec durant la décomposition: {} {}".format(
                        valeur, decomposeur.chaine
                    )
                )
                continue

        LOGGER.debug("exec decomposition obj resultant : {}".format(self.obj))
        return (decomposition_reussie, sortir)

    def _score_max_infos(self, obj, poids=None):
        """Estime la quantité d'informations portée par un objet décomposé.

        Algo :

        * modificateur lié au poids du décomposeur en cours ; 2 pour l'objet
          déjà décomposé, afin de favoriser les infos préexistantes ;
        * nombre de champs non vides : bonus au plus rempli ;
        * longueur des infos de l'objet relativement à l'objet témoin.

        Ce qui rapporte le plus est le nombre de champs non vides.

        TODO : le code d'origine calculait aussi un « bonus de longueur » (+1
        si l'objet est plus gros que le témoin, pour éviter qu'un objet vide
        soit mieux noté) mais **ne l'ajoutait jamais** à la somme — variable
        morte relevée par ruff (F841) à la remontée. Le comportement est
        conservé tel quel ici ; l'intégrer relève d'un arbitrage à part, car
        cela change le classement des décompositions.

        :param poids: poids du décomposeur, ou None pour l'objet déjà décomposé
        """
        modificateur = 2 if poids is None else poids

        nb_champs_non_vides = 2 * len([v for v in _valeurs_champs(obj) if v])

        longueur_relative = len(pickle.dumps(obj)) / len(pickle.dumps(self.obj_temoin))
        return longueur_relative + modificateur + nb_champs_non_vides

    def identifie(
        self,
        racine=None,
        options_resultat=DECOMPOSE_RESULTAT_PREMIER_NON_NUL,
        options_analyse=DECOMPOSE_ANALYSE_ARBO_UN_NIVEAU,
    ):
        """Identifie l'objet donné à partir des décomposeurs donnés.

        Options de décomposition :

        * premier non nul pour 1 niveau
        * premier non nul pour plusieurs niveaux successifs
        * plusieurs résultats pour 1 niveau
        * plusieurs résultats pour tous les niveaux
        * premier non nul pour la juxtaposition des niveaux

        Reste : juxtaposition + successifs ? TODO ?

        :param options_analyse: une constante `DECOMPOSE_ANALYSE_*`, ou une
                                collection de constantes pour les cumuler
        :raise DecompositionEchecTousPatrons: si aucun patron n'aboutit
        """
        # Une seule option est le cas courant ; on normalise pour que le test
        # d'appartenance ci-dessous soit une vraie appartenance et non une
        # recherche de sous-chaîne.
        if isinstance(options_analyse, str):
            options_analyse = (options_analyse,)

        # Première décomposition :
        succes, sortir = self._exec_decomposition(options_resultat=options_resultat)
        if sortir is not _CONTINUER:
            return sortir

        # TODO par défaut on prend self.obj.source et basename comme valeurs
        # on pourrait en prendre d'autres et/ou le rendre paramétrable
        #
        # `remonte_arborescence` lève `ValueError` si le fichier n'est pas sous
        # `racine` : c'est un échec d'**analyse** (cette racine ne s'applique
        # pas), pas une panne. On le traduit donc en « rien trouvé par cette
        # option » plutôt que de laisser l'exception interrompre la boucle. #116
        if DECOMPOSE_ANALYSE_ARBO_COMPLETE in options_analyse:
            try:
                for parent in remonte_arborescence(self.obj.source, racine):
                    succes_, sortir = self._exec_decomposition(
                        options_resultat=options_resultat, valeur=parent.name
                    )
                    succes = succes if succes else succes_
                    if sortir is not _CONTINUER:
                        return sortir
            except ValueError:
                LOGGER.debug("racine %r ne contient pas le fichier", racine)
        if DECOMPOSE_ANALYSE_ARBO_CONCATENE in options_analyse:
            valeur_orig = self.obj.basename
            try:
                for parent in remonte_arborescence(self.obj.source, racine):
                    valeur_orig = "{} {}".format(parent.name, valeur_orig)
                    succes_, sortir = self._exec_decomposition(
                        options_resultat=options_resultat, valeur=valeur_orig
                    )
                    succes = succes if succes else succes_
                    if sortir is not _CONTINUER:
                        return sortir
            except ValueError:
                LOGGER.debug("racine %r ne contient pas le fichier", racine)
        # TODO comparer les infos trouvées et ne garder que la meilleure
        # Pour l'instant on fait comme filebot : on s'arrête à la première.

        # comme on attrape les exceptions, si on ne trouve rien on arrive ici
        if not succes:
            raise DecompositionEchecTousPatrons()
        return None
