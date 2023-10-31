# automatheque.factrice

Librairie et app simplifiée d'envoi de mail

## Détail

La librairie fournit des Preparatrices pour transformer un Courriel en objet "email" manipulable
et des Expeditrices pour envoyer cet email "concret", par ex avec un SMTP ou avec le logiciel esmtp
etc.

Ainsi qu'une application factrice qui permet d'envoyer un mail simplement à partir de la conf
automatheque.

## TODO

On peut passer les expeditrices et preparatrices en Greffon, afin de pouvoir
déterminer directement depuis une conf quel greffon utiliser.

En gros: 

* soit je mets une conf dans l'app cible qui décide d'utiliser telle ou telle expeditrice
* soit je mets une conf dans l'app cible qui est passée directement à la fabrique d'envoi (ce
    qui me semble pas mal) (attention cependant, si l'app ajoute un nouveau greffon, il y a
    eventuellement un risque de sécurité ? ou au contraire on veut pouvoir le surcharger ?)

## Requirement

Python >=3.8

## Installation

```bash
pip install automatheque.factrice
```

## License

GPLv3
