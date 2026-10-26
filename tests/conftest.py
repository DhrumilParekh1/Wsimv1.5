import pytest
from wrestling_sim.starter import new_game


@pytest.fixture
def world():
    return new_game(seed=6789)
