# -*- coding: utf-8 -*-
import abc
import os
import smtplib
from configparser import ConfigParser
from datetime import datetime
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Optional

import attr
from automatheque.configuration import NoOptionError, charge_configuration
from automatheque.log import recup_logger
from automatheque.schema.texte import Courriel
from automatheque.util.dependances_externes import charge_dependance, Executant

from automatheque.factrice.preparation import PreparatriceSmtp, SEPARATEUR_DESTINATAIRES

LOGGER = recup_logger(__name__)


class Expeditrice(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def expedie(self, courriel: Courriel):
        raise NotImplementedError


@attr.s
class ExpeditriceSmtp(Expeditrice):
    """Expédie un Courriel par SMTP.

    :param config: ConfigParser avec la configuration d'expédition, voir plus bas le format
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
    oauth_cmd=/chemin/vers/script/generation_token # TODO livrer en dépendances ?
    oauth_client_id=XyXyXyX
    ```
    """

    config: ConfigParser = attr.ib(default=None)  # TODO validator
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
            # Les identifiants ne sont pas renseignés en conf, on vérifie que c'est voulu
            if self.config.getboolean("factrice.smtp", "anonyme", default=False):
                pass
            LOGGER.exception("no options")
        except Exception as e:
            LOGGER.exception(e)
            # TODO etre plus fin dans l'exception
            pass

    def __connecter(self):
        """Identifie l'utilisateur sur le SMTP donné.

        Utilise le couple login/mdp ou le jeton xoauth2 (grosso modo un Auth Bearer encodé en b64).
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
            oauth_jeton = Executant(cmd).exec(*args).stdout.decode("utf-8").strip("\n")
            # LOGGER.debug("jeton oauth : " + oauth_jeton)
            self.s.ehlo(oauth_client_id)
            # On pourrait utiliser self.s.auth, mais il faut travailler directement avec la chaine xoauth2
            # non encodée en b64.
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

    def envoyer_courriel(cls):
        """décorateur envoi mail ??"""
        pass


@attr.s
class ExpeditriceEsmtp:
    config: ConfigParser = attr.ib(default=None)  # TODO validator

    def __attrs_post_init__(self):
        self.config = self.config if self.config else charge_configuration()
        self.executant: Executant = charge_dependance("esmtp", "esmtp", "")

    def __gen_fichier(
        self, courriel: Courriel, fichier_sortie: Optional[Path] = None
    ) -> Path:
        """Génère un fichier temporaire à donner à esmtp.

        :return: Path du fichier
        """
        if courriel.emetteur is None:
            courriel.emetteur = "osuser@localhost"  # TODO ?

        date = datetime.now().strftime("%Y%m%d-%H%M%s")
        # TODO nom fic
        fic = fichier_sortie or Path("/tmp/") / f"{date}_{courriel.sujet}.txt"
        with open(fic, "w") as f:
            contenu = PreparatriceSmtp().prepare(courriel).as_string()
            f.write(contenu)

        return fic

    def expedie(self, courriel: Courriel):
        # envoi du mail si esmtp est paramétré
        # cmd = 'cat "{0}" | esmtp {1}'.format(
        #    self__.gen_fichier(courriel), SEPARATEUR_DESTINATAIRES.join(courriel.destinataires)
        # )
        args = [SEPARATEUR_DESTINATAIRES.join(courriel.destinataires)]
        fic = self.__gen_fichier(courriel)
        with open(fic, "r") as f:
            # On execute : `esmtp courriel1,courriel2 < fic`
            process = self.executant.exec(*args, stdin=f)

        try:
            process.check_returncode()  # TODO attention raise !
        except Exception as e:
            LOGGER.exception(process.stderr)
            # raise e
        return process.returncode
