# Automathèque

Code de base pour `automatheque`.

## Installation

mais il est peu probable que vous ayez besoin de l'installer, c'est avant tout une dépendance.

```shell
pip install automatheque
```

### Dépendances

* voir ```pyproject.toml```

### Install en mode dev

`pip install -e .[dev,docs]` ou `monas install` depuis la racine.

## Usage : Utilitaire pour script

```python
from automatheque.script import script  # alias court de script_automatheque

@script(__doc__, __version__)
def main(_script):
    print(_script.config)

if __name__ == '__main__':
    main()
```

> L'API a été promue de `automatheque.util.script` vers `automatheque.script`
> (#41). L'ancien chemin reste importable (shim) mais émet un
> `DeprecationWarning` : migrez vers `from automatheque.script import script`.

Le décorateur câble automatiquement, si le script les déclare dans son usage :
`--dry-run` (via `_script.dry_run`), la verbosité `-v`/`-q` (niveau de log), une
sortie propre sur `Ctrl-C` (code 130), et la durée d'exécution.

### Sous-commandes (via commandopt)

On déclare des fonctions-commandes avec `@commande([...])` (alias de
`commandopt.commandopt`) et on aiguille avec `_script.execute_commande()`. Les
options internes d'automatheque (`--config`, `--dry-run`, `-v`/`-q`) sont
exclues de la sélection, mais restent transmises à la commande.

```python
"""Mon script

Usage:
  mon_script.py (--ajouter | --supprimer) [--config=<f>] [-v]
"""
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

if __name__ == '__main__':
    main()
```
