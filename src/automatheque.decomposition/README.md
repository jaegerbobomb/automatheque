# automatheque.decomposition

Décomposition de chaînes et d'arborescences par patrons.

## Détail

Décomposer, c'est extraire des informations d'une chaîne — le plus souvent le
chemin d'un fichier — en lui appliquant une série d'expressions rationnelles,
puis reverser le résultat dans un objet.

Typiquement : retrouver le nom d'une série et son numéro d'épisode dans
`/media/series/Ma Serie/S01/E02.avi`, ou l'album et le lieu d'une photo dans
son arborescence de rangement.

Le paquet ne touche pas au système de fichiers : il ne manipule que des
chaînes. Un chemin lui est donné, il en tire des informations ; c'est
l'appelant qui décide ensuite quoi en faire — le déplacement du fichier est
l'affaire de `automatheque.renommage`, l'opération symétrique.

C'est aussi pourquoi les deux sont des distributions séparées : indexer ou
étiqueter sans jamais déplacer un fichier est un usage courant, qui n'a pas à
tirer les dépendances du renommage.

## Les briques

* **`Decomposeur`** — un patron : une expression rationnelle, un appel qui
  fournit la chaîne à analyser, un appel qui reverse le résultat dans l'objet,
  et un poids pour départager les patrons concurrents.
* **`Decomposeurs`** — un jeu de patrons, itérable. À sous-classer pour
  décrire une famille de médias (séries, films, photos…).
* **`Decomposable`** — mixin à faire hériter par l'objet à décomposer. Il doit
  exposer `basename` (la chaîne analysée par défaut) et `filename` (le chemin
  complet, remonté niveau par niveau).
* **`Identificateur`** — l'algorithme : il joue les patrons sur l'objet selon
  les options demandées, et choisit la décomposition la plus pertinente.

## Options

Deux familles d'options se combinent.

Ce qu'on garde du résultat :

| Constante | Effet |
|---|---|
| `DECOMPOSE_RESULTAT_PREMIER_NON_NUL` | s'arrête au premier patron qui trouve quelque chose |
| `DECOMPOSE_RESULTAT_CUMULE` | applique tous les patrons qui trouvent quelque chose |
| `DECOMPOSE_RESULTAT_MAX_INFOS` | garde la décomposition qui remplit le plus l'objet |

Ce qu'on analyse :

| Constante | Effet |
|---|---|
| `DECOMPOSE_ANALYSE_ARBO_UN_NIVEAU` | le `basename` seul |
| `DECOMPOSE_ANALYSE_ARBO_COMPLETE` | chaque niveau de l'arborescence, un par un |
| `DECOMPOSE_ANALYSE_ARBO_CONCATENE` | les niveaux concaténés, de proche en proche |

`Decomposable.auto_decompose()` essaie ces combinaisons de la plus riche à la
plus simple, et s'arrête à la première qui aboutit.

## Exemple

```py
import attr

from automatheque.decomposition import Decomposable, Decomposeur, Decomposeurs


def _remplit(obj, resultats):
    obj.serie, obj.saison, obj.episode = resultats


class SerieDecomposeurs(Decomposeurs):
    def __attrs_post_init__(self):
        self.decomposeurs = [
            Decomposeur(r"(.+)[. ]S(\d{2})E(\d{2})", _remplit),
        ]


@attr.s
class Episode(Decomposable):
    filename = attr.ib(default="")
    basename = attr.ib(default="")
    serie = attr.ib(default=None)
    saison = attr.ib(default=None)
    episode = attr.ib(default=None)


ep = Episode(filename="/media/Ma.Serie.S01E02.avi", basename="Ma.Serie.S01E02.avi")
ep.decompose(decomposeurs=SerieDecomposeurs())
# ep.serie == "Ma.Serie", ep.saison == "01", ep.episode == "02"
```

## Requirement

Python >=3.9

## Installation

```bash
pip install automatheque.decomposition
```

## License

LGPLv3.0 ou ultérieure
