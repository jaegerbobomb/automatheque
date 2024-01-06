from copy import deepcopy

from automatheque.conception.structures import Fabrique, Monteur
from automatheque.configuration import charge_configuration, ConfigParser
from automatheque.greffon.greffon import Greffon
from automatheque.log import recup_logger


LOGGER = recup_logger(__name__)


class FabriqueGreffon(Fabrique):
    """Classe qui permet d'instancier les Greffons dont les Monteur ont été enregistrés.

    Il faut dans un premier temps enregistrer les monteurs des greffons par la fonction
    enregistre_greffons, puis il faut activer le greffon donné ce qui lance
    `monteur.cree()` avec les arguments donnés.

    À défaut de Monteur, on peut donner la classe qui sera instanciée directement.
    Dans les deux cas il faut que la classe ait une propriété "clé".

    Si on utilise un Monteur, on peut utiliser la même clé que le Greffon, tant qu'elle
    n'est pas utilisée par plusieurs Greffons ou Monteurs, puisqu'elle servira à
    déclencher l'instanciation du Monteur ou du Greffon associée.

    .. example::
        >>> from automatheque.greffon import fabrique_greffon
        >>> fabrique_greffon.charge_monteurs([
               "plugin1.monteur.Monteur1",
               "plugin2.monteur.Monteur2"
            ])
        >>> plugin1_id1 = fabrique_greffon.active(
               "monteur1",
               *args,
               identifiant="plugin1_identifiant1",
               **kwargs
            )
        >>> plugin1_id1.appel_quelconque_capacite()
    """

    def active(self, cle_monteur, *args, identifiant=None, **kwargs):
        """Va chercher dans le registre des greffons et renvoie le greffon activé.

        S'il ne trouve pas le greffon il en instancie un autre.
        TODO : comme identifiant peut etre auto génré on devrait pouvoir
        le rendre facultatif si on ne veut pas l'appeler nommément ? ou mettre clé ?
        """
        if not identifiant or identifiant not in Greffon.greffons_identifiants():
            # greffons.keys():
            try:
                if identifiant:
                    kwargs["identifiant"] = identifiant
                instance_greffon = self.cree(cle_monteur, *args, **kwargs)
                LOGGER.debug(f"Greffon activé : {instance_greffon}")
                if not instance_greffon.actif:
                    LOGGER.warning(f"Greffon {instance_greffon} inactif")
                    return False
                identifiant = instance_greffon.identifiant
            except Exception:
                LOGGER.exception(f"Echec activation greffon : {identifiant}")
        return Greffon.greffon_par_identifiant(identifiant)

    def charge_monteurs(self, liste_monteurs):
        """Enregistre les monteurs de greffons disponibles dans la fabrique.

        Cela  pourrait etre fait de manière automatique, par ex en scannant un
        répertoire.
        Dans tous les cas ensuite il faut les activer un par un dans la configuration.
        """
        monteurs = []
        for elem in liste_monteurs:
            from pydoc import locate

            monteur = locate(elem)  # ou importlib TODO ?
            if issubclass(monteur, Greffon):
                monteur_concret = monteur
            elif issubclass(monteur, Monteur):
                monteur_concret = monteur()  # Il faut instancier le Monteur
            else:
                raise ValueError(
                    "La fabrique ne peut charger que des Greffons ou des Monteurs"
                )
            monteurs.append(self.enregistre_monteur(monteur.cle, monteur_concret))
        return monteurs

    # def greffons_charge_defaut(self):
    #    """Charge les greffons par défaut dans la liste de monteurs."""
    #    self.enregistre_greffons(LISTE_GREFFONS_DEFAUT)
    #    LOGGER.debug(f"Greffons chargés : {self.recup_monteurs()}")

    def active_greffons_conf(self, liste_greffons=None, configuration=None):
        """Active les greffons qui sont définis en conf dans l'option "greffons".

        Si on utilise cette méthode pour activer les greffons, alors il est nécessaire
        de fournir un identifiant, on ne peut pas laisser automatheque créer l'identifiant
        automatiquement.

        .. example::
            [greffons]
            # liste d'identifiants des greffons, il peut y avoir plusieurs identifiants
            # pour le même greffon, par exemple avec des arguments différents
            greffons=kodi1,trakt1

            [kodi1]
            # clé du monteur ou du plugin
            greffon=kodi
            # Argument supplémentaire fourni à l'instanciation
            hote=xxx
            [trakt1]
            greffon=trakt

        configuration peut aussi être un dictionnaire équivalent.
        """
        if configuration is None:
            configuration = dict(charge_configuration())
        elif isinstance(configuration, ConfigParser):
            configuration = dict(configuration)
        elif not isinstance(configuration, dict):
            raise ValueError("'configuration' n'est pas au bon format")

        if liste_greffons is None:
            try:
                # On laisse dans "greffon" si on veut sortir le code un jour !
                liste_greffons = configuration.get("greffons").get("greffons")
                liste_greffons = [i.strip() for i in liste_greffons.split(",")]
            except Exception as e:
                LOGGER.exception(e)
                raise ValueError(f"pas de liste de greffons dans {configuration}")

        greffons_actifs = []
        for identifiant in liste_greffons:
            conf = deepcopy(configuration.get(identifiant))
            cle = conf.pop("greffon")
            greffons_actifs.append(self.active(cle, identifiant=identifiant, **conf))
        return greffons_actifs


fabrique_greffon = FabriqueGreffon()
