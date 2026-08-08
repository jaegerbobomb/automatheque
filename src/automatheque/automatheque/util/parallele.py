# -*- coding: utf-8 -*-
"""Exécution parallèle bornée, avec limite de débit.

Besoin récurrent en scripting : lancer N tâches **en parallèle** — souvent des
appels réseau — sans saturer une API ni la machine. `parallelise` applique une
fonction à chaque élément d'une collection sur un pool borné, en option sous une
**limite de débit** (« ≤ 5 appels/seconde »), et **collecte les exceptions par
tâche** plutôt que de s'arrêter au premier échec.

Exemple ::

    from automatheque.util import parallelise, reessaye

    @reessaye(tentatives=3, exceptions=(ConnectionError,))
    def telecharge(url):
        ...

    resultats = parallelise(telecharge, urls, workers=8, debit=5)
    reussis = [r.valeur for r in resultats if r.reussi]
    for echec in (r for r in resultats if not r.reussi):
        LOGGER.warning("%s : %s", echec.element, echec.erreur)

Se compose naturellement avec `reessaye` (#7) : décorer la fonction suffit.
"""

import logging
import threading
import time
from concurrent.futures import (
    ProcessPoolExecutor,
    ThreadPoolExecutor,
    as_completed,
)
from typing import Any, Callable, Dict, Iterable, List, Optional

import attr

LOGGER = logging.getLogger(__name__)


@attr.s
class Resultat:
    """Le résultat d'une tâche : sa valeur, **ou** l'exception qu'elle a levée.

    `valeur` vaut `None` aussi bien pour une tâche qui a renvoyé `None` que pour
    une tâche en échec : c'est `reussi` (et non `valeur`) qui distingue les deux.
    """

    element = attr.ib()
    valeur = attr.ib(default=None)
    erreur: Optional[BaseException] = attr.ib(default=None)

    @property
    def reussi(self) -> bool:
        """Vrai si la tâche s'est terminée sans exception."""
        return self.erreur is None

    def valeur_ou_leve(self):
        """Renvoie la valeur, ou **relève** l'exception si la tâche a échoué."""
        if self.erreur is not None:
            raise self.erreur
        return self.valeur


class _LimiteurDebit:
    """Espace les départs pour ne pas dépasser `debit` appels par seconde.

    Chaque tâche appelle `attend()` avant de partir. Le calcul de l'instant du
    prochain départ autorisé est sérialisé sous verrou ; l'attente proprement
    dite se fait **hors** du verrou, pour ne pas bloquer les autres.
    """

    def __init__(self, debit: float):
        self._intervalle = 1.0 / debit
        self._verrou = threading.Lock()
        self._prochain_depart = 0.0

    def attend(self) -> None:
        with self._verrou:
            maintenant = time.monotonic()
            depart = max(maintenant, self._prochain_depart)
            self._prochain_depart = depart + self._intervalle
            a_patienter = depart - maintenant
        if a_patienter > 0:
            time.sleep(a_patienter)


def parallelise(
    fonction: Callable[[Any], Any],
    elements: Iterable[Any],
    *,
    workers: Optional[int] = None,
    debit: Optional[float] = None,
    processus: bool = False,
) -> List[Resultat]:
    """Applique `fonction` à chaque élément, en parallèle et borné.

    Les résultats sont renvoyés **dans l'ordre des éléments**, chacun enveloppé
    dans un :class:`Resultat` (valeur ou exception). Une tâche qui échoue
    n'interrompt pas les autres.

    :param fonction: appelée en `fonction(element)` pour chaque élément.
    :param elements: itérable d'entrées (consommé en entier au départ).
    :param workers: nombre maximal de tâches simultanées. `None` (défaut) laisse
        l'exécuteur choisir.
    :param debit: limite de débit, en **appels par seconde** ; les départs sont
        espacés en conséquence. `None` (défaut) ne limite pas.
    :param processus: `True` pour un pool de **processus** (tâches gourmandes en
        CPU) au lieu de threads (défaut, adapté aux entrées/sorties). En mode
        processus, `fonction` et les éléments doivent être *picklables*.
    :return: la liste des :class:`Resultat`, dans l'ordre des éléments.
    :raise ValueError: si `workers` < 1, ou si `debit` <= 0.
    """
    if workers is not None and workers < 1:
        raise ValueError("workers doit être >= 1")
    if debit is not None and debit <= 0:
        raise ValueError("debit doit être > 0 (appels par seconde)")

    elements = list(elements)
    if not elements:
        return []

    limiteur = _LimiteurDebit(debit) if debit else None
    classe_executeur = ProcessPoolExecutor if processus else ThreadPoolExecutor
    par_index: Dict[int, Resultat] = {}

    with classe_executeur(max_workers=workers) as executeur:
        # Le débit est régulé au **départ** (dans ce thread) : la cadence de
        # soumission borne la cadence de démarrage, quel que soit le nombre de
        # workers, et fonctionne aussi bien avec un pool de processus.
        futur_vers_index = {}
        for index, element in enumerate(elements):
            if limiteur is not None:
                limiteur.attend()
            futur_vers_index[executeur.submit(fonction, element)] = index

        for futur in as_completed(futur_vers_index):
            index = futur_vers_index[futur]
            element = elements[index]
            try:
                par_index[index] = Resultat(element, valeur=futur.result())
            except Exception as exc:
                LOGGER.debug("Tâche %r a échoué : %s", element, exc)
                par_index[index] = Resultat(element, erreur=exc)

    return [par_index[i] for i in range(len(elements))]
