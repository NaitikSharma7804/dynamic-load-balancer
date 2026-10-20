"""
Base interface for load-balancing algorithms.

Every load-balancing strategy must implement the select()
method. This allows the proxy engine to use different
algorithms without knowing their internal implementation.
"""

from abc import ABC, abstractmethod
from typing import Any


class SelectionStrategy(ABC):
    """
    Abstract base class for backend selection algorithms.

    Implementations include:

    - Round Robin
    - Smooth Weighted Round Robin
    - Least Connections
    - IP Hash
    """

    @abstractmethod
    def select(
        self,
        backends: list[Any],
        request: Any = None,
    ) -> Any:
        """
        Select one backend from the available backend list.

        Parameters
        ----------
        backends:
            List of currently available backend objects.

        request:
            Optional incoming request. Some algorithms, such as
            IP Hash, can use request information when selecting
            a backend.

        Returns
        -------
        Any
            The selected backend.

        Raises
        ------
        NotImplementedError
            If a subclass does not implement this method.
        """

        raise NotImplementedError(
            "SelectionStrategy subclasses must implement select()."
        )