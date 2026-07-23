# -*- coding: utf-8 -*-
import abc
import logging
import os
import smtplib
import subprocess
import tempfile
from configparser import ConfigParser
from pathlib import Path
from typing import Optional

import attr

from automatheque.configuration import NoOptionError, charge_configuration
from automatheque.factrice.preparation import SEPARATEUR_DESTINATAIRES, PreparatriceSmtp
from automatheque.schema.texte import Courriel
from automatheque.util.dependances_externes import Executant, charge_dependance
from automatheque.util.fichier import enleve_caracteres_invalides

LOGGER = logging.getLogger(__name__)


class Expeditrice(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def expedie(self, courriel: Courriel):
        raise NotImplementedError


@attr.s
class ExpeditriceSmtp(Expeditrice):
    """Expédie un Courriel par SMTP.

    :param config: ConfigParser avec la configuration d'expédition, voir plus bas
        le format
    :type ConfigParser:

    ```ini
    [factrice.smtp]
    ssl=1
    hote=https://url_smtp
    # défaut 465 si ssl = 1, sinon 25
    port=465

    # Connexion
    # Cas 1 : anonyme
    # défaut à 0, smtp non anonyme
    anonyme=0

    # Cas 2 : identifiant mdp
    identifiant=xxx
    mdp=yyy

    # Cas 3 : token oauth
    # défaut à false
    oauth=0
    # BYO : commande externe qui écrit le jeton OAuth2 sur stdout (p. ex. `oama`
    # ou un script perso). Sa présence est vérifiée via charge_dependance (#27).
    oauth_cmd=/chemin/vers/oama_ou_script_generation_token
    oauth_client_id=XyXyXyX
    ```
    """

    config: ConfigParser = attr.ib(
        default=None,
        validator=attr.validators.optional(attr.validators.instance_of(ConfigParser)),
    )
    s: smtplib.SMTP = attr.ib(init=False)
    preparatrice = attr.ib(init=False, default=PreparatriceSmtp)

    def __attrs_post_init__(self):
        self.config: ConfigParser = (
            self.config if self.config else charge_configuration()
        )
        if not self.config.has_section("factrice.smtp"):
            raise Exception("Configuration [factrice.smtp] manquante")

        if self.config.getboolean("factrice.smtp", "ssl", fallback=False):
            self.s = smtplib.SMTP_SSL(
                self.config.get("factrice.smtp", "hote", fallback="localhost"),
                self.config.get("factrice.smtp", "port", fallback=465),
            )
        else:
            self.s = smtplib.SMTP(
                self.config.get("factrice.smtp", "hote", fallback="localhost"),
                self.config.get("factrice.smtp", "port", fallback=25),
            )
            try:
                self.s.starttls()
            except smtplib.SMTPNotSupportedError:
                LOGGER.warning("Attention le smtp ne gère pas le TLS.")

        try:
            self.__connecter()
        except NoOptionError:
            # Les identifiants ne sont pas renseignés en conf, on vérifie que
            # c'est voulu
            if self.config.getboolean("factrice.smtp", "anonyme", fallback=False):
                pass
            LOGGER.exception("no options")
        except smtplib.SMTPException:
            LOGGER.exception("Échec de la connexion au serveur SMTP.")

    def __connecter(self):
        """Identifie l'utilisateur sur le SMTP donné.

        Utilise le couple login/mdp ou le jeton xoauth2 (grosso modo un Auth
        Bearer encodé en b64).
        """
        LOGGER.debug("__connecter")
        oauth = self.config.getboolean("factrice.smtp", "oauth", fallback=False)
        oauth_cmd = self.config.get("factrice.smtp", "oauth_cmd", fallback=None)
        oauth_client_id = self.config.get(
            "factrice.smtp", "oauth_client_id", fallback=None
        )

        self.s.set_debuglevel(1)

        if oauth and oauth_cmd is not None and oauth_client_id is not None:
            cmd, *args = oauth_cmd.split(" ")
            # `oauth_cmd` est **fourni par l'utilisateur** (BYO) : un générateur
            # de jeton OAuth2 pour le mail (p. ex. `oama`) ou un script perso —
            # automatheque n'embarque pas d'outil OAuth. On passe par
            # `charge_dependance` (plutôt qu'un `Executant` brut) pour **vérifier
            # que la commande est installée** et lever une erreur claire
            # (`DependanceManquante`) sinon, au lieu d'un échec subprocess
            # obscur. Cf. #27.
            executant = charge_dependance(
                "factrice.oauth",
                cmd,
                cmd,
                erreur=(
                    f"L'outil de génération de jeton OAuth « {cmd} » (oauth_cmd) "
                    "est introuvable. Installez-le (p. ex. oama) ou corrigez le "
                    "chemin dans [factrice.smtp] oauth_cmd."
                ),
            )
            oauth_jeton = executant.exec(*args, encoding="utf-8").stdout.strip("\n")
            # LOGGER.debug("jeton oauth : " + oauth_jeton)
            self.s.ehlo(oauth_client_id)
            # On pourrait utiliser self.s.auth, mais il faut travailler
            # directement avec la chaine xoauth2 non encodée en b64.
            self.s.docmd("AUTH", "XOAUTH2 " + oauth_jeton)
        else:
            self.s.login(
                self.config.get("factrice.smtp", "identifiant"),
                self.config.get("factrice.smtp", "mdp"),
            )

    def expedie(self, courriel: Courriel):
        """Envoie le courriel."""
        # Envoie le courriel au serveur SMTP configuré.
        if courriel.emetteur is None:
            courriel.emetteur = self.config.get(
                "factrice.smtp", "identifiant", fallback="atmtq"
            )
        res = self.s.sendmail(
            courriel.emetteur,
            courriel.destinataires,
            self.preparatrice.prepare(courriel).as_string(),
        )
        if res:
            LOGGER.warning(res)
        self.s.quit()


@attr.s
class ExpeditriceEsmtp:
    config: ConfigParser = attr.ib(
        default=None,
        validator=attr.validators.optional(attr.validators.instance_of(ConfigParser)),
    )

    def __attrs_post_init__(self):
        self.config = self.config if self.config else charge_configuration()
        self.executant: Executant = charge_dependance("esmtp", "esmtp", "")

    def __gen_fichier(
        self, courriel: Courriel, fichier_sortie: Optional[Path] = None
    ) -> Path:
        """Génère un fichier à donner à esmtp (contenu du courriel préparé).

        L'émetteur par défaut est configurable via ``[factrice.esmtp] emetteur``
        (repli historique ``osuser@localhost``). Cf. #27.

        Sans ``fichier_sortie`` explicite, un fichier temporaire **unique** est
        créé via :func:`tempfile.mkstemp` dans le répertoire temporaire système
        (fini le ``/tmp`` codé en dur et les collisions de noms) ; le sujet,
        assaini, ne sert que de préfixe lisible. Cf. #27.

        :return: Path du fichier
        """
        if courriel.emetteur is None:
            courriel.emetteur = self.config.get(
                "factrice.esmtp", "emetteur", fallback="osuser@localhost"
            )

        contenu = PreparatriceSmtp().prepare(courriel).as_string()

        if fichier_sortie is not None:
            fic = Path(fichier_sortie)
            fic.write_text(contenu)
            return fic

        sujet_sain = enleve_caracteres_invalides(courriel.sujet or "courriel")
        fd, chemin = tempfile.mkstemp(prefix=f"factrice_{sujet_sain}_", suffix=".txt")
        with os.fdopen(fd, "w") as f:
            f.write(contenu)
        return Path(chemin)

    def expedie(self, courriel: Courriel):
        # envoi du mail si esmtp est paramétré
        # cmd = 'cat "{0}" | esmtp {1}'.format(
        #    self__.gen_fichier(courriel),
        #    SEPARATEUR_DESTINATAIRES.join(courriel.destinataires)
        # )
        args = [SEPARATEUR_DESTINATAIRES.join(courriel.destinataires)]
        fic = self.__gen_fichier(courriel)
        with open(fic, "r") as f:
            # On execute : `esmtp courriel1,courriel2 < fic`
            process = self.executant.exec(*args, stdin=f)

        # `check_returncode()` lève `CalledProcessError` si esmtp a échoué. On
        # l'attrape spécifiquement pour journaliser proprement (code + stderr)
        # sans interrompre l'appelant : `expedie` renvoie le code de retour,
        # charge à lui de décider quoi en faire.
        try:
            process.check_returncode()
        except subprocess.CalledProcessError:
            LOGGER.error(
                "Échec de l'envoi via esmtp (code %s) : %s",
                process.returncode,
                process.stderr,
            )
        return process.returncode
