# automatheque.renommage

Renommage et rangement de fichiers par gabarits.

## Détail

Un **gabarit** est un squelette de chemin — `{date:%Y}/{album}/{nom}` —
assorti d'une condition qui dit quand il s'applique et d'un ordre qui le
priorise. Le **renommeur** choisit le premier gabarit applicable, en déduit un
nouveau chemin, et y déplace le fichier.

C'est l'opération symétrique de `automatheque.decomposition` : là où celle-ci
tire des métadonnées d'un chemin, celle-ci construit un chemin à partir de
métadonnées. Les deux sont des distributions séparées parce que seule
celle-ci écrit sur le disque : un consommateur qui indexe sans jamais déplacer
n'a pas à en dépendre.

## Les briques

* **`Gabarit`** — un squelette, une condition, un ordre.
* **`Gabarits`** — la liste des gabarits, et l'algorithme de choix : d'abord
  ceux dont la condition est vérifiée, classés par ordre, puis ceux qui n'ont
  pas de condition. Un gabarit sans condition est donc un filet de sécurité,
  pas un concurrent.
* **`Renommable`** — mixin à faire hériter par l'objet à ranger. Il expose
  `filename` et surcharge `_gabarits_par_defaut()` et `_liste_champs_dispo()`.
* **`Renommeur`** — le déplacement lui-même.

## Exemple

```py
import attr

from automatheque.renommage import Gabarit, Gabarits, Renommable


@attr.s
class Photo(Renommable):
    album = attr.ib(default="", kw_only=True)
    annee = attr.ib(default="", kw_only=True)

    @classmethod
    def _gabarits_par_defaut(cls):
        return Gabarits(
            [
                Gabarit(
                    squelette="{annee}/{album}/{nom}", condition='"{album}"', ordre=1
                ),
                Gabarit(squelette="a-trier/{nom}", ordre=9),
            ]
        )

    def _liste_champs_dispo(self):
        return {"album": self.album, "annee": self.annee, "nom": ...}


photo = Photo(filename="/entree/DSC_0001.jpg", album="Japon", annee="2013")
photo.renomme("/photos")
# /photos/2013/Japon/DSC_0001.jpg
```

## La configuration est reçue, pas cherchée

Les gabarits vivent souvent dans un fichier de configuration :

```ini
[renommage]
r1 = ['{annee}/{album}/{nom}', '"{album}"', 1]
r2 = ['a-trier/{nom}', '', 9]
```

`Gabarits.depuis_configuration(config, section)` les en tire, et le résultat
est **passé** au renommeur :

```py
gabarits = Gabarits.depuis_configuration(charge_configuration(), "renommage")
Renommeur(photo, gabarits=gabarits).renomme("/photos")
```

Le renommeur ne consulte aucun état global : c'est l'appelant qui décide d'où
viennent ses gabarits. Le code d'origine appelait `charge_configuration()`
lui-même — une localisation de service, qui rendait le renommage dépendant
d'un fichier de configuration présent au bon endroit, et intestable sans lui.

## Ce que le renommage ne fait pas

* **Il n'écrit pas d'attributs étendus.** Le code d'origine posait
  discrètement `user.automatheque.fichier_orig` et
  `user.automatheque.modele.classe` dans les xattr du fichier, à chaque
  renommage. Les xattr ne survivent ni à la plupart des copies, ni aux
  archives, ni aux transferts réseau : c'est le plus fragile des supports pour
  de la provenance. Conserver le nom d'origine relève de l'application, qui
  sait où elle range ses métadonnées.
* **Il ne modifie pas le contenu du fichier.** Écrire des étiquettes dans une
  image est l'affaire d'un adaptateur.

## Transfert

Le déplacement est une copie, suivie d'une vérification de taille, suivie de
la suppression de l'original. `shutil.move` seul ne dirait pas si la copie
s'est mal passée d'un système de fichiers à l'autre ; ici, une cible qui ne
correspond pas lève `TransfertIncomplet` **et laisse l'original en place**.

## Requirement

Python >=3.9

## Installation

```bash
pip install automatheque.renommage
```

## License

LGPLv3.0 ou ultérieure
