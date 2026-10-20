import hashlib

from .base import SelectionStrategy


class IPHash(SelectionStrategy):

    def select(
        self,
        backends,
        request=None,
    ):
        """
        Select a backend using a SHA-256 hash
        of the client IP address.

        Supports:
        1. FastAPI Request objects
        2. Dictionary-style test requests
        3. Objects containing client_ip
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

        client_ip = "unknown"

        if isinstance(request, dict):

            client_ip = request.get(
                "client_ip",
                "unknown",
            )

        elif request is not None:

            if hasattr(request, "client_ip"):

                client_ip = (
                    request.client_ip
                )

            elif hasattr(request, "client"):

                if request.client is not None:

                    client_ip = (
                        request.client.host
                    )

        key = client_ip.encode(
            "utf-8"
        )

        digest = hashlib.sha256(
            key
        ).hexdigest()

        hash_value = int(
            digest,
            16,
        )

        index = (
            hash_value
            % len(usable_backends)
        )

        return usable_backends[index]