#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""factrice

Application pour envoyer des mails simplement en utilisant la connexion
configurée dans config.ini.

Le texte du mail peut être passé en argument **ou** via l'entrée standard, ce
qui permet un usage en tuyau : ``cat contenu | factrice sujet adresse``. Cf. #27.

Usage:
  factrice [--via-esmtp] <sujet> <adresse_mail_cible> [<texte_du_mail>]

Options:
  -h --help
  <adresse_mail_cible>  Adresse mail ou liste d'adresses séparées par des , sans espace
  <texte_du_mail>       Corps du mail ; si omis, lu sur l'entrée standard.
  --via-esmtp
"""

import sys

from automatheque.factrice.expedition import ExpeditriceEsmtp, ExpeditriceSmtp
from automatheque.schema.texte.courriel import Courriel
from automatheque.script import ScriptAutomatheque, script_automatheque

__version__ = "0.0.1"


def recupere_texte(arguments):
    """Renvoie le texte du mail : l'argument s'il est fourni, sinon ``stdin``.

    Permet ``cat contenu | factrice sujet adresse`` (le corps arrive alors sur
    l'entrée standard). Cf. #27.
    """
    texte = arguments["<texte_du_mail>"]
    if texte is None:
        texte = sys.stdin.read()
    return texte


def envoi_mail_simple(sujet, adresse, txt, via_esmtp=False):
    """Envoie un mail simple."""
    destinataires = adresse.split(",")
    mail = Courriel(sujet=sujet, destinataires=destinataires)
    mail.contenu = txt

    if not via_esmtp:
        ExpeditriceSmtp().expedie(mail)
        return

    # envoi du mail si esmtp est paramétré
    # cmd = 'cat "{0}" | esmtp {1}'.format(
    #    mail.gen_fichier(), SEPARATEUR_DESTINATAIRES.join(mail.destinataires)
    # )
    # return_code = subprocess.call(cmd, shell=True)
    return_code = ExpeditriceEsmtp().expedie(mail)
    return return_code


def traite(_script: ScriptAutomatheque = None):
    """Corps du script : config déjà chargée et arguments parsés par le décorateur."""
    _script.logger.debug(_script.arguments)

    envoi_mail_simple(
        _script.arguments["<sujet>"],
        _script.arguments["<adresse_mail_cible>"],
        recupere_texte(_script.arguments),
        _script.arguments["--via-esmtp"],
    )


def main():
    """Point d'entrée console de ``factrice`` (cf. ``[project.scripts]``).

    Le câblage ``@script_automatheque`` est fait **ici**, à l'appel, et non à
    l'import du module : importer ``automatheque.factrice.app`` ne déclenche donc
    plus le parsing d'``argv`` ni la (re)configuration du logging — le module
    redevient importable (et testable). Cf. #27.
    """
    return script_automatheque(__doc__, __version__)(traite)()


if __name__ == "__main__":
    main()
