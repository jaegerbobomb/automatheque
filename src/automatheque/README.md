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
from automatheque.util.script import script_automatheque

# préparation de l'annotation en haut du fichier :
script_automatheque = script_automatheque(__doc__, __version__)

@script_automatheque
def main(_script):
    print(_script.config)

if __name__ == '__main__':
    main()
```
