"""
Load-balancing algorithm package.

Exports all available selection strategies.
"""

from .base import SelectionStrategy
from .round_robin import RoundRobin
from .weighted_rr import SmoothWeightedRoundRobin
from .least_conn import LeastConnections
from .ip_hash import IPHash


__all__ = [
    "SelectionStrategy",
    "RoundRobin",
    "SmoothWeightedRoundRobin",
    "LeastConnections",
    "IPHash",
]