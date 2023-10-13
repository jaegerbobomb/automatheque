#!/usr/bin/env python
"""Module pour le patron Registre.

Ce patron permet de garder un registre de toutes les instances des sous-classes
d'une classe donnée.

.. usage ::

    class RegistreElements(metaclass=MetaInstanceRegistre):
        pass

    class Element(RegistreElements):
        pass


Une instance de Element va être enregistrée dans RegistreElements._instances ou
RegistreElements._recup_instances().
Il s'agit d'un set que l'on peut ensuite parcourir pour trouver celle que l'on
souhaite.

NB: La classe fille doit être hashable. Si l'on utilise attrs il faut penser à déclarer
    @attr.s(eq=False) pour activer le hashage.
"""

import weakref


class MetaClasseRegistre(type):
    """Metaclass fournissant un registre de **classes**.

    inspiré de https://stackoverflow.com/a/48328119
    """

    def __init__(cls, name, bases, attrs):
        # Create class
        super(MetaInstanceRegistre, cls).__init__(name, bases, attrs)

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

    def _recup_classes(cls, recursive=False):
        """Get all instances of this class in the registry.

        If recursive=True search subclasses recursively"""
        classes = list(cls._classes)
        if recursive:
            for child in cls.__subclasses__():
                classes += child._recup_classes(recursive=recursive)

        # Remove duplicates from multiple inheritance.
        return list(set(classes))


class MetaInstanceRegistre(type):
    """Metaclass fournissant un registre **d'instances**.

    https://stackoverflow.com/a/48328119

    exemple d'implémentation dans automatheque.plugin
    """

    def __init__(cls, name, bases, attrs):
        # Create class
        super(MetaInstanceRegistre, cls).__init__(name, bases, attrs)

        # Initialize fresh instance storage, no need to have a weak ref for now
        cls._instances = set()

    def __call__(cls, *args, **kwargs):
        # Create instance (calls __init__ and __new__ methods)
        inst = super(MetaInstanceRegistre, cls).__call__(*args, **kwargs)

        cls._instances.add(inst)

        return inst

    def _recup_instances(cls, recursive=False):
        """Get all instances of this class in the registry.

        If recursive=True search subclasses recursively"""
        instances = list(cls._instances)
        if recursive:
            for child in cls.__subclasses__():
                instances += child._recup_instances(recursive=recursive)

        # Remove duplicates from multiple inheritance.
        return list(set(instances))
