import random
import pytest


@pytest.fixture
def rng():
    """Deterministic RNG seeded at 0 for any test that needs randomness."""
    return random.Random(0)


@pytest.fixture
def rng_factory():
    """Returns a factory that produces fresh Random(seed) per call."""
    return lambda seed: random.Random(seed)
