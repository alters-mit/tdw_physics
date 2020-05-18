from typing import Dict


class ObjectPosition:
    """
    Defines the initial position of an object.
    """

    def __init__(self, position: Dict[str, float], radius: float):
        """
        :param position: The position of the object.
        :param radius: The maximum radius swept by the object's bounds.
        """

        self.position = position
        self.radius = radius
