"""
Round Robin load-balancing algorithm.

Round Robin distributes requests sequentially across all
available backend servers.

Example with three backends:

    Request 1 -> b1
    Request 2 -> b2
    Request 3 -> b3
    Request 4 -> b1
    Request 5 -> b2
    Request 6 -> b3
"""

from .base import SelectionStrategy


class RoundRobin(SelectionStrategy):
    """
    Basic Round Robin backend selection.

    The algorithm maintains an internal index. Every time
    select() is called, the index moves to the next backend.
    """

    def __init__(self) -> None:
        """Initialize the backend selection index."""

        self._index = 0

    def select(
        self,
        backends,
        request=None,
    ):
        """
        Select the next backend using Round Robin.

        Parameters
        ----------
        backends:
            List of currently healthy/available backends.

        request:
            Incoming request. It is not required by Round Robin,
            but is accepted to follow the common strategy interface.

        Returns
        -------
        Backend | None
            The next backend, or None if no backend is available.
        """

        if not backends:
            return None

        # Make sure the index is always inside the current
        # backend list.
        self._index %= len(backends)

        backend = backends[self._index]

        # Move to the next backend for the next request.
        self._index = (self._index + 1) % len(backends)

        return backend