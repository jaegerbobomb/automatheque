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


if __name__ == "__main__":
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
def ajouter(arguments): ...


@commande(["--supprimer"])
def supprimer(arguments): ...


@script(__doc__, __version__)
def main(_script):
    return _script.execute_commande()


if __name__ == "__main__":
    main()
```

## Gestion des secrets

Un mot de passe ou un jeton ne doit **jamais** fuiter dans les logs ou une
traceback, et sa **source** ne devrait pas être figée dans le code (parfois une
variable d'environnement, parfois la config, parfois un trousseau système…).
Le module `automatheque.secret` répond aux deux besoins.

### `Secret` : une valeur qui ne fuite pas

`Secret` enveloppe une valeur sensible : son `repr`, son `str`, un f-string et le
logging affichent tous `***`. La valeur réelle n'est accessible qu'au **point
d'usage**, via `.reveler()`.

```python
from automatheque.secret import Secret

mdp = Secret("s3cr3t")
print(mdp)  # ***
print(f"mdp={mdp}")  # mdp=***
logging.info("mdp=%s", mdp)  # …mdp=***  (pas de fuite dans les logs)

connexion.login("moi", mdp.reveler())  # .reveler() UNIQUEMENT ici
```

### `recup_secret` : d'où vient le secret ?

`recup_secret(cle, config=, resolveurs=)` cherche la valeur auprès de plusieurs
sources **essayées dans l'ordre** (premier gagnant) et renvoie un `Secret` (ou
`None` si introuvable). Par défaut : la **variable d'environnement** puis, si on
lui passe une `config`, la **configuration**.

```python
from automatheque.secret import recup_secret

# factrice.smtp.mdp  →  variable FACTRICE_SMTP_MDP,
#                       sinon [factrice.smtp] mdp = … dans la config
mdp = recup_secret("factrice.smtp.mdp", config=_script.config)
if mdp is not None:
    serveur.login(user, mdp.reveler())
```

### Les sources sont des greffons

Chaque source est un **greffon** (cf. `automatheque.greffon`) rendant la capacité
`ResoudreSecret` — on ajoute donc une nouvelle source comme n'importe quel
greffon. Fournis d'origine :

| Greffon                 | Source                                                        |
| ----------------------- | ------------------------------------------------------------- |
| `GreffonSecretEnv`      | variable d'env (`factrice.smtp.mdp` → `FACTRICE_SMTP_MDP`)     |
| `GreffonSecretConfig`   | configuration (`section.option`)                              |
| `GreffonSecretKeyring`  | trousseau système (dépendance optionnelle `keyring`)          |
| `GreffonSecretCommande` | sortie d'une commande externe (p. ex. `pass show {cle}`)      |

Pour un ordre ou des sources personnalisés, on passe `resolveurs=` (liste
ordonnée de greffons) — ici on interroge d'abord le trousseau, puis une commande :

```python
from automatheque.secret import (
    recup_secret,
    GreffonSecretKeyring,
    GreffonSecretCommande,
)

mdp = recup_secret(
    "factrice.smtp.mdp",
    resolveurs=[
        GreffonSecretKeyring(service="mon-appli"),
        GreffonSecretCommande(gabarit="pass show {cle}"),
    ],
)
```

### Caviardage des logs (défense en profondeur)

La configuration de log par défaut (`configure_logging_defaut()`, appelée par un
script `@script_automatheque`) installe un **filtre de caviardage** : si la
valeur d'un `Secret` vivant apparaît dans un message de log, elle est remplacée
par `***`.

```python
mdp = recup_secret("factrice.smtp.mdp", config=_script.config)
logging.getLogger(__name__).info("connexion mdp=%s", mdp.reveler())
# → journalisé : « connexion mdp=*** »  (même la valeur révélée est rattrapée)
```

La première ligne de défense reste de ne jamais logger un secret en clair
(`Secret` est déjà caviardé par `str`/`repr`) ; le filtre rattrape les fuites
indirectes. Si tu configures le logging toi-même (dictConfig maison), pose le
filtre sur tes handlers avec `installe_caviardage()` :

```python
from automatheque.log import installe_caviardage

installe_caviardage()  # racine par défaut (couvre les loggers enfants)
```

### Un secret dans une section de configuration

Une section de configuration porte souvent la valeur la plus sensible de
l'application (mot de passe SMTP, clé d'API, jeton). Dans une classe de section
(cf. [`charge_section`](#configuration--sections-typées-et-validées)), on la
déclare avec `Secret` en **converteur** : la valeur est enveloppée dès le
chargement, donc caviardée partout où la classe est affichée.

```python
import attr
from automatheque.configuration import charge_section
from automatheque.secret import Secret


@attr.s
class ConfigSmtp:
    hote = attr.ib()
    mdp = attr.ib(converter=Secret)
    jeton = attr.ib(default=None, converter=attr.converters.optional(Secret))


smtp = charge_section(ConfigSmtp, _script.config, "smtp")
smtp  # ConfigSmtp(hote='smtp.exemple.org', mdp=Secret(***), jeton=None)
serveur.login(smtp.hote, smtp.mdp.reveler())  # .reveler() au point d'usage
```

Sans cela l'option reste une **chaîne nue** : elle ressort telle quelle dans le
`repr` de la classe — donc dans une traceback ou un `LOGGER.debug("config=%s",
reglages)` — et le filtre de caviardage ne la rattrape pas, puisqu'il ne connaît
que les `Secret` vivants.

`Secret` et `recup_secret` répondent à deux questions différentes ; ils se
composent, ils ne se remplacent pas :

| | Question | Quand |
| - | -------- | ----- |
| `converter=Secret` | « cette option est-elle sensible ? » | la valeur vit dans le `.ini` |
| `recup_secret`     | « d'où vient la valeur ? »           | env d'abord, puis config, trousseau… |

Une option secrète écrite dans le `.ini` doit de toute façon être **déclarée**
dans la classe : en mode strict (le défaut), `charge_section` refuse une option
inconnue. Autant la déclarer avec `converter=Secret`.

## Configuration : sections typées et validées

`_script.config` (ou `charge_configuration()`) renvoie un `ConfigParser` **brut** :
tout y est chaîne, rien n'est validé, et une clé absente ou mal typée n'explose
que **tard**, au point d'accès. Pour valider **tôt** — et récupérer des valeurs
déjà typées — décris une section comme une classe `attrs` et peuple-la avec
`charge_section` :

```python
import attr
from automatheque.configuration import charge_section, booleen, liste


@attr.s
class ConfigSmtp:
    hote = attr.ib(validator=attr.validators.instance_of(str))
    port = attr.ib(default=465, converter=int)
    tls = attr.ib(default=True, converter=booleen)
    relais = attr.ib(factory=list, converter=liste)


smtp = charge_section(ConfigSmtp, _script.config, "smtp")
smtp.port  # 587 : un int, pas "587"
smtp.tls  # True : un bool
```

pour la section :

```ini
[smtp]
hote   = smtp.exemple.org
port   = 587
tls    = yes
relais = a.exemple.org, b.exemple.org
```

Une option **sensible** (mot de passe, jeton, clé d'API) se déclare avec `Secret`
en converteur, pour qu'elle ne fuite ni par le `repr` de la classe ni par une
traceback : cf. [Un secret dans une section de
configuration](#un-secret-dans-une-section-de-configuration).

Les `converter`/`validator` des `attr.ib` font la conversion (chaîne → `int`,
`booleen`, `liste`…) et le contrôle. L'erreur est **précoce et nommée** :

- section absente, **option inconnue** (une faute de frappe est rattrapée),
  **clé requise manquante**, ou valeur refusée par un converter/validator →
  `ConfigurationInvalide` (qui hérite de `ValueError`), avec le nom de la section
  et de la clé fautive.
- `charge_section(..., strict=False)` **ignore** les options inconnues, quand une
  même section sert à plusieurs consommateurs.

Deux converteurs sont fournis, puisqu'un `.ini` ne rend que des chaînes :

| Converteur | `.ini` → | reconnaît |
| ---------- | -------- | --------- |
| `booleen`  | `bool`      | `yes/no`, `true/false`, `on/off`, `oui/non`, `vrai/faux` |
| `liste`    | `list[str]` | valeurs séparées par des virgules (éléments vides ignorés) |

### Valider la configuration d'un greffon

Un greffon peut **exiger** une configuration (`config_requise = True`). Plutôt
que de se fier au contrôle générique « une config existe-t-elle ? »
(`Greffon.actif`), décris la config attendue **par une classe** et valide-la avec
`charge_section` au moment de monter le greffon : on sait alors **tôt**, et
précisément, si la config requise est réellement présente et bien typée.

C'est le rôle naturel d'un **Monteur** — il lit la configuration et s'en sert
pour instancier le greffon :

```python
import attr
from automatheque.configuration import charge_configuration, charge_section
from automatheque.conception.structures import Monteur
from automatheque.greffon import Greffon


@attr.s
class ConfigMeteo:
    """Config attendue par le greffon météo (section [meteo])."""

    cle_api = attr.ib(validator=attr.validators.instance_of(str))
    hote = attr.ib(default="api.exemple.org", converter=str)


@attr.s(eq=False)
class GreffonMeteo(Greffon):
    config_requise = attr.ib(default=True, init=False, kw_only=True)
    reglages = attr.ib(default=None, kw_only=True)  # ConfigMeteo validée


class MonteurMeteo(Monteur):
    """Lit la config et ne monte le greffon que si sa section est valide."""

    def construit(self, *, identifiant=None, **kwargs):
        # charge_section lève ConfigurationInvalide — tôt, nommée — si la
        # section [meteo] est absente, incomplète ou mal typée.
        reglages = charge_section(ConfigMeteo, charge_configuration(), "meteo")
        return GreffonMeteo(identifiant=identifiant, reglages=reglages, **kwargs)
```

Le paquet déclare le monteur en point d'entrée (auto-découverte, cf.
`decouvre_monteurs`) :

```toml
[project.entry-points."automatheque.greffons"]
meteo = "mon_paquet.meteo:MonteurMeteo"
```

Ainsi `config_requise` cesse d'être un simple booléen « il y a une config » : la
présence **réelle** des clés dont ce greffon a besoin est prouvée à l'instanciation,
et une config manquante ou fautive échoue avec un message qui nomme la section et
la clé.

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
