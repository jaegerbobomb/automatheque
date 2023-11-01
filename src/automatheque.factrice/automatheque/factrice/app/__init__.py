#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""factrice

Application pour envoyer des mails simplement en utilisant la connexion configurée dans config.ini.

TODO pouvoir faire `cat contenu | factrice sujet email`

Usage:
  factrice [--via-esmtp] <sujet> <adresse_mail_cible> <texte_du_mail>

Options:
  -h --help
  <adresse_mail_cible>  Adresse mail ou liste d'adresses séparées par des , sans espace
  --via-esmtp
"""

import subprocess

from automatheque.schema.texte.courriel import Courriel
from automatheque.util.script import script_automatheque, ScriptAutomatheque

from automatheque.factrice.expedition import ExpeditriceEsmtp, ExpeditriceSmtp

__version__ = "0.0.1"


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


@script_automatheque(__doc__, __version__)
def main(_script: ScriptAutomatheque = None):
    _script.logger.debug(_script.arguments)

    envoi_mail_simple(
        _script.arguments["<sujet>"],
        _script.arguments["<adresse_mail_cible>"],
        _script.arguments["<texte_du_mail>"],
        _script.arguments["--via-esmtp"],
    )


if __name__ == "__main__":
    main()
