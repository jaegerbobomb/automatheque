#!/usr/bin/env python
"""Module pour le patron Registre.

Ce patron permet de garder un registre de toutes les instances des sous-classes
d'une classe donnée.

.. usage ::

    class RegistreElements(metaclass=MetaInstanceRegistre):
        pass

    class Element(RegistreElements):
        pass


Une instance de Element va être enregistrée dans RegistreElements.__instances
que l'on peut parcourir grâce à RegistreElements._instances(inclure_enfants=True).

NB: On peut également utiliser Element._instances() pour avoir accès à toutes les
instances d'Element.

Le stockage se fait dans un **dict utilisé comme ensemble ordonné** (les valeurs
sont ignorées) : on **dédoublonne** les instances tout en **préservant l'ordre
d'insertion**. `_instances()` renvoie donc les instances dans l'ordre où elles
ont été créées, ce qui rend déterministes les recherches qui s'appuient dessus
(p. ex. `greffons_par_capacite`).

NB: La classe fille doit être hashable. Si l'on utilise attrs il faut penser à déclarer
    @attr.s(eq=False) pour activer le hashage.
"""

import weakref


class MetaClasseRegistre(type):
    """Metaclass fournissant un registre de **classes**.

    inspiré de https://stackoverflow.com/a/48328119

    NB: non testé.
    """

    def __init__(cls, name, bases, attrs):
        # Create class
        super(MetaClasseRegistre, cls).__init__(name, bases, attrs)

        # Initialize fresh instance storage
        cls._classes = weakref.WeakValueDictionary()

    def __new__(cls, name, bases, attrs):
        new_cls = type.__new__(cls, name, bases, attrs)
        """
            Here the name of the class is used as key but it could be any class
            parameter.
        """

        # Store weak reference to class. WeakValueDictionnary will automatically remove
        # references to objects that have been garbage collected
        cls._classes[new_cls.__name__] = new_cls
        return new_cls

    def _recup_classes(cls, inclure_enfants=False):
        """Get all instances of this class in the registry.

        Si inclure_enfants=True, on renvoie aussi les instances des sous-classes.
        """
        classes = [] + list(cls._classes)[cls.__name__]
        if inclure_enfants:
            for child in cls.__subclasses__():
                classes += child._recup_classes(inclure_enfants=inclure_enfants)

        # Remove duplicates from multiple inheritance.
        return list(set(classes))


class MetaInstanceRegistre(type):
    """Metaclass fournissant un registre **d'instances**.

    source: https://stackoverflow.com/a/48328119

    Ici on utilise un "weakRefSet", donc on garde le registre de toutes les instances
    "en cours d'utilisation", ie dont on a encore la référence.
    Si on écrase la référence ou que l'on n'en a pas, alors l'instance disparaît du
    registre lors du passage du ramasse-miettes.

    NB: on peut préférer la composition (au lieu de l'héritage) dans ce genre de cas
        mais cette façon de faire me semble très "pythonesque" malgré tout.
    """

    def __init__(cls, name, bases, attrs):
        # Lors de la création **de la classe** du registre (et pas de l'instance)
        super(MetaInstanceRegistre, cls).__init__(name, bases, attrs)

        # Stockage "weak ref" **ordonné** : une WeakKeyDictionary (adossée à un
        # dict) dédoublonne et préserve l'ordre d'insertion, là où une WeakSet
        # perdrait l'ordre. Les instances non référencées ailleurs disparaissent
        # au passage du ramasse-miettes.
        cls.__instances = weakref.WeakKeyDictionary()

    def __call__(cls, *args, **kwargs):
        # Crée l'instance (appelle les méthodes __init__ et __new__)
        inst = super(MetaInstanceRegistre, cls).__call__(*args, **kwargs)

        cls.__instances[inst] = None  # inst doit être hashable

        return inst

    def _instances(cls, inclure_enfants=False):
        """Renvoie les instances de **cette classe** stockées dans le registre.

        Si inclure_enfants=True, on renvoie aussi les instances des sous-classes.
        L'ordre d'insertion (ordre de création) est **préservé**.
        """
        if not inclure_enfants:
            # Aucun doublon possible au sein du registre d'une seule classe :
            # pas de dédoublonnage, donc aucun re-hachage des instances
            # (coûteux pour des objets gelés profonds, hachés à chaque appel).
            return list(cls.__instances)

        instances = list(cls.__instances)
        for child in cls.__subclasses__():
            instances += child._instances(inclure_enfants=inclure_enfants)

        # Dédoublonne (héritage multiple) EN préservant l'ordre d'insertion.
        return list(dict.fromkeys(instances))

    def nombre_instances(cls, inclure_enfants=True):
        """Le nombre d'instances au registre, sans les matérialiser.

        Contrairement à ``len(cls._instances(...))``, ne construit ni ne
        re-hache aucune instance : O(1) par classe. Sert d'étalon
        d'invalidation de cache : le nombre bouge dès qu'une instance est créée
        (registre persistant) — ou libérée au ramasse-miettes (registre faible).

        NB : en cas d'héritage en losange, les doublons entre registres
        d'enfants rendent ce nombre majorant (il reste stable tant que rien
        n'est créé, donc valable comme étalon) ;
        ``len(cls._instances(inclure_enfants=True))`` fait foi pour un
        dénombrement exact.
        """
        total = len(cls.__instances)
        if inclure_enfants:
            for child in cls.__subclasses__():
                total += child.nombre_instances(inclure_enfants=True)
        return total

    def purge_instances(cls, inclure_enfants=True):
        """Vide le registre : l'API publique de remise à zéro.

        Cas d'usage : l'isolation des tests et les rechargements — les
        consommateurs n'ont plus à toucher au conteneur interne via son nom
        manglé, qui reste un détail d'implémentation (``set`` jusqu'en 0.18,
        dict-ensemble-ordonné depuis 0.19 : chaque changement les cassait).

        Vide **en place** : les références déjà prises sur le conteneur
        restent valides.
        """
        cls.__instances.clear()
        if inclure_enfants:
            for child in cls.__subclasses__():
                child.purge_instances(inclure_enfants=True)


class MetaInstancePersistanteRegistre(type):
    """Metaclass fournissant un registre **d'instances**.

    source: https://stackoverflow.com/a/48328119

    exemple d'implémentation dans automatheque.plugin

    Ici on utilise un "set" et non un "weakRefSet", pour le cas où on ne garde **pas**
    les références des instances crées : on les stocke juste dans le registre et on les
    cherche ensuite.
    Avec un weakRefSet on garde le registre de toutes les instances "en cours
    d'utilisation",
    (ie dont on a encore la référence).

    >>> class A(metaclass=MetaInstancePersistanteRegistre):
    >>>   pass
    >>> class B(metaclass=MetaInstanceRegistre):
    >>>   pass
    >>> a = A()
    >>> b = B()
    >>> A() # out: <__main__.A object at 0x7fcbc181b810>
    >>> B() # out: <__main__.B object at 0x7fcbc181a390>
    >>> A._instances()  # les 2 instances
    [<__main__.A object at 0x7fcbc181b810>, <__main__.A object at 0x7fcbc1a62d50>]
    >>> B._instances()  # une seule instance
    [<__main__.B object at 0x7fcbc181a3d0>]


    NB: on peut préférer la composition (au lieu de l'héritage) dans ce genre de cas
        mais cette façon de faire me semble très "pythonesque" malgré tout.
    """

    def __init__(cls, name, bases, attrs):
        # Lors de la création **de la classe** du registre (et pas de l'instance)
        super(MetaInstancePersistanteRegistre, cls).__init__(name, bases, attrs)

        # Stockage des instances dans un dict utilisé comme **ensemble ordonné**
        # (valeurs ignorées) : on dédoublonne SANS perdre l'ordre d'insertion
        # (un `set` déduplique mais perd l'ordre). Pas besoin de "weak ref" ici.
        cls.__instances = {}

    def __call__(cls, *args, **kwargs):
        # Crée l'instance (appelle les méthodes __init__ et __new__)
        inst = super(MetaInstancePersistanteRegistre, cls).__call__(*args, **kwargs)

        cls.__instances[inst] = None  # inst doit être hashable

        return inst

    def _instances(cls, inclure_enfants=False):
        """Renvoie les instances de **cette classe** stockées dans le registre.

        Si inclure_enfants=True, on renvoie aussi les instances des sous-classes.
        L'ordre d'insertion (ordre de création) est **préservé**.
        """
        if not inclure_enfants:
            # Aucun doublon possible au sein du registre d'une seule classe :
            # pas de dédoublonnage, donc aucun re-hachage des instances
            # (coûteux pour des objets gelés profonds, hachés à chaque appel).
            return list(cls.__instances)

        instances = list(cls.__instances)
        for child in cls.__subclasses__():
            instances += child._instances(inclure_enfants=inclure_enfants)

        # Dédoublonne (héritage multiple) EN préservant l'ordre d'insertion.
        return list(dict.fromkeys(instances))

    def nombre_instances(cls, inclure_enfants=True):
        """Le nombre d'instances au registre, sans les matérialiser.

        Contrairement à ``len(cls._instances(...))``, ne construit ni ne
        re-hache aucune instance : O(1) par classe. Sert d'étalon
        d'invalidation de cache : le nombre bouge dès qu'une instance est créée
        (registre persistant) — ou libérée au ramasse-miettes (registre faible).

        NB : en cas d'héritage en losange, les doublons entre registres
        d'enfants rendent ce nombre majorant (il reste stable tant que rien
        n'est créé, donc valable comme étalon) ;
        ``len(cls._instances(inclure_enfants=True))`` fait foi pour un
        dénombrement exact.
        """
        total = len(cls.__instances)
        if inclure_enfants:
            for child in cls.__subclasses__():
                total += child.nombre_instances(inclure_enfants=True)
        return total

    def purge_instances(cls, inclure_enfants=True):
        """Vide le registre : l'API publique de remise à zéro.

        Cas d'usage : l'isolation des tests et les rechargements — les
        consommateurs n'ont plus à toucher au conteneur interne via son nom
        manglé, qui reste un détail d'implémentation (``set`` jusqu'en 0.18,
        dict-ensemble-ordonné depuis 0.19 : chaque changement les cassait).

        Vide **en place** : les références déjà prises sur le conteneur
        restent valides.
        """
        cls.__instances.clear()
        if inclure_enfants:
            for child in cls.__subclasses__():
                child.purge_instances(inclure_enfants=True)
