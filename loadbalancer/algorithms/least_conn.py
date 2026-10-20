"""
Least Connections load-balancing algorithm.

The algorithm sends a new request to the backend currently
handling the smallest number of active connections.

For weighted backends, the effective load is calculated as:

    active_connections / effective_weight

This allows a more powerful backend with a higher weight
to handle proportionally more connections.
"""

from .base import SelectionStrategy


class LeastConnections(SelectionStrategy):
    """
    Least Connections backend selection strategy.
    """

    def select(
        self,
        backends,
        request=None,
    ):
        """
        Select the backend with the lowest effective connection load.

        Parameters
        ----------
        backends:
            List of available backend objects.

        request:
            Incoming request. Not required by Least Connections.

        Returns
        -------
        Backend | None
            Backend with the lowest effective connection count.
        """

        if not backends:
            return None

        usable_backends = [
            backend
            for backend in backends
            if backend.effective_weight > 0
        ]

        if not usable_backends:
            return None

        return min(
            usable_backends,
            key=lambda backend: (
                backend.active_connections
                / max(1, backend.effective_weight),

                # Name provides deterministic tie-breaking.
                backend.name,
            ),
        )