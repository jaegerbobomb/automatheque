# Contribuer à Automathèque

Merci de votre intérêt pour le projet ! Ce document décrit les quelques règles
à suivre pour proposer une contribution.

## Licence des contributions

Automathèque est distribué sous **GNU LGPL v3 ou ultérieure**
(`LGPL-3.0-or-later`, cf. [`LICENSE`](LICENSE) et [`GPL-3.0.txt`](GPL-3.0.txt)).
Toute contribution est acceptée et distribuée sous cette même licence.

## Certificat d'origine (DCO)

Pour garder le projet sain juridiquement — et préserver la possibilité de faire
évoluer la licence à l'avenir — chaque contribution doit être **certifiée via le
[Developer Certificate of Origin](https://developercertificate.org/) (DCO)**
plutôt qu'un CLA. C'est léger : vous certifiez simplement avoir le droit de
soumettre le code, sans céder vos droits d'auteur.

Concrètement, ajoutez une ligne `Signed-off-by` à chacun de vos commits :

```
Signed-off-by: Prénom Nom <email@exemple.org>
```

Git le fait automatiquement avec l'option `-s` :

```sh
git commit -s -m "feat: mon changement"
```

Le nom et l'email doivent être réels et correspondre à votre identité git. En
signant, vous attestez le texte du DCO ci-dessous.

<details>
<summary>Texte du Developer Certificate of Origin, version 1.1</summary>

```
Developer Certificate of Origin
Version 1.1

Copyright (C) 2004, 2006 The Linux Foundation and its contributors.

Everyone is permitted to copy and distribute verbatim copies of this
license document, but changing it is not allowed.


Developer's Certificate of Origin 1.1

By making a contribution to this project, I certify that:

(a) The contribution was created in whole or in part by me and I
    have the right to submit it under the open source license
    indicated in the file; or

(b) The contribution is based upon previous work that, to the best
    of my knowledge, is covered under an appropriate open source
    license and I have the right under that license to submit that
    work with modifications, whether created in whole or in part
    by me, under the same open source license (unless I am
    permitted to submit under a different license), as indicated
    in the file; or

(c) The contribution was provided directly to me by some other
    person who certified (a), (b) or (c) and I have not modified
    it.

(d) I understand and agree that this project and the contribution
    are public and that a record of the contribution (including all
    personal information I submit with it, including my sign-off) is
    maintained indefinitely and may be redistributed consistent with
    this project or the open source license(s) involved.
```

</details>

## Style et qualité

* Le code suit `ruff` (lint + format) et vise la conformité `mypy` — voir le job
  `qualite` de la CI.
* Les nouvelles fonctionnalités et corrections viennent avec des tests
  (`pytest src`).
* Les messages de commit et le journal suivent
  [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) : pensez à ajouter
  une entrée dans le `CHANGELOG` du paquet concerné, sous `[Unreleased]`.
