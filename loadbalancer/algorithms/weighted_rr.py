"""
Smooth Weighted Round Robin load-balancing algorithm.

The algorithm gives each backend a configured weight and
distributes requests proportionally.

Example:

    b1 -> weight 5
    b2 -> weight 3
    b3 -> weight 1

Over a large number of requests, the distribution approaches:

    b1 -> 5/9
    b2 -> 3/9
    b3 -> 1/9

The implementation uses the Smooth Weighted Round Robin
technique used by systems such as Nginx.
"""

from .base import SelectionStrategy


class SmoothWeightedRoundRobin(SelectionStrategy):
    """
    Smooth Weighted Round Robin strategy.

    Unlike simple weighted round robin, this algorithm avoids
    sending several requests to the same high-weight server
    consecutively whenever possible.
    """

    def __init__(self) -> None:
        """
        Initialize the current-weight state.

        Each backend has its own running current weight.
        """

        self._current_weights: dict[str, int] = {}

    def select(
        self,
        backends,
        request=None,
    ):
        """
        Select a backend using Smooth Weighted Round Robin.

        Parameters
        ----------
        backends:
            List of available backend objects.

        request:
            Incoming request. Not required by this algorithm.

        Returns
        -------
        Backend | None
            Selected backend, or None if no backend exists.
        """

        if not backends:
            return None

        total_weight = 0
        selected_backend = None
        selected_weight = None

        for backend in backends:
            weight = max(0, backend.effective_weight)

            if weight <= 0:
                continue

            # Initialize state for a newly added backend.
            if backend.name not in self._current_weights:
                self._current_weights[backend.name] = 0

            # Increase current weight by configured weight.
            self._current_weights[backend.name] += weight

            total_weight += weight

            current = self._current_weights[backend.name]

            # Select the backend with the highest current weight.
            if (
                selected_backend is None
                or current > selected_weight
            ):
                selected_backend = backend
                selected_weight = current

        if selected_backend is None:
            return None

        # Subtract total weight from the selected backend.
        self._current_weights[selected_backend.name] -= total_weight

        return selected_backend