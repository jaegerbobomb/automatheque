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

## Configuration du logging

Automathèque **ne configure rien à l'import** (une bibliothèque ne doit pas
toucher au logging global). C'est **l'application** qui configure : un script
décoré par `@script_automatheque` appelle `configure_logging_defaut()` (sortie
console) puis applique la section `[log]` de sa configuration.

Un script étant une application, sa configuration de log vise la **racine** :
`logging.getLogger(__name__)` dans le script **et** les loggers des dépendances
en héritent.

### Forme simple (inline dans le `.ini`)

Dans le `config.ini` du script (`~/.config/<mon_script>/config.ini`) :

```ini
[log]
niveau = INFO
fichier = mon_script.log          ; optionnel (sinon console)
format  = %%(asctime)s [%%(levelname)s] %%(name)s: %%(message)s
; niveaux par logger (nom seul = niveau global) :
names   = automatheque:WARNING, mon_script:DEBUG, requests:ERROR
```

> Dans un `.ini`, les `%` se doublent en `%%` (convention ConfigParser) ; un `%`
> non échappé lève une erreur explicite.

Un seul handler/destination est partagé ; `names` n'ajuste que des **niveaux**.

### Forme complète (dictConfig externe)

Pour router des loggers vers des **destinations différentes** (erreurs du script
dans un fichier, automatheque ailleurs…), pointer vers un dictConfig complet
(JSON **ou** YAML, détecté au contenu) :

```ini
[log]
fichier_config = log.yaml
```

Voir l'exemple canonique [`log.yaml.dist`](log.yaml.dist).
