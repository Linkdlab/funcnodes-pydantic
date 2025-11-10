import pytest
from pytest_funcnodes import nodetest, all_nodes_tested
import funcnodes_core as fn
import funcnodes_pydantic as fnmodule  # noqa


def test_all_nodes_tested(all_nodes):
        all_nodes_tested(all_nodes, fnmodule.NODE_SHELF,ignore=[])
