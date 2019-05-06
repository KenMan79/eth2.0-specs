import pytest

import eth2spec.phase0.spec as spec

from eth2spec.phase0.spec import (
    ZERO_HASH,
    process_deposit,
)
from tests.helpers import (
    get_balance,
    build_deposit,
    privkeys,
    pubkeys,
)

from tests.context import spec_state_test


def prepare_state_and_deposit(state, validator_index, amount):
    """
    Prepare the state for the deposit, and create a deposit for the given validator, depositing the given amount.
    """
    pre_validator_count = len(state.validator_registry)
    # fill previous deposits with zero-hash
    deposit_data_leaves = [ZERO_HASH] * pre_validator_count

    pubkey = pubkeys[validator_index]
    privkey = privkeys[validator_index]
    deposit, root, deposit_data_leaves = build_deposit(
        state,
        deposit_data_leaves,
        pubkey,
        privkey,
        amount,
    )

    state.latest_eth1_data.deposit_root = root
    state.latest_eth1_data.deposit_count = len(deposit_data_leaves)
    return deposit


def run_deposit_processing(state, deposit, validator_index, valid=True):
    """
    Run ``process_deposit``, yielding:
      - pre-state ('pre')
      - deposit ('deposit')
      - post-state ('post').
    If ``valid == False``, run expecting ``AssertionError``
    """
    pre_balance = get_balance(state, validator_index)
    pre_validator_count = len(state.validator_registry)

    yield 'pre', state
    yield 'deposit', deposit

    if not valid:
        with pytest.raises(AssertionError):
            process_deposit(state, deposit)
        yield 'post', None
        return

    process_deposit(state, deposit)

    yield 'post', state

    assert len(state.validator_registry) == pre_validator_count
    assert len(state.balances) == pre_validator_count
    assert state.deposit_index == state.latest_eth1_data.deposit_count
    assert get_balance(state, validator_index) == pre_balance + deposit.amount


@spec_state_test
def test_success(state):
    # fresh deposit = next validator index = validator appended to registry
    validator_index = len(state.validator_registry)
    amount = spec.MAX_EFFECTIVE_BALANCE
    deposit = prepare_state_and_deposit(state, validator_index, amount)

    yield from run_deposit_processing(state, deposit, validator_index)


@spec_state_test
def test_success_top_up(state):
    validator_index = 0
    amount = spec.MAX_EFFECTIVE_BALANCE // 4
    deposit = prepare_state_and_deposit(state, validator_index, amount)

    yield from run_deposit_processing(state, deposit, validator_index)


@spec_state_test
def test_wrong_index(state):
    validator_index = len(state.validator_registry)
    amount = spec.MAX_EFFECTIVE_BALANCE
    deposit = prepare_state_and_deposit(state, validator_index, amount)

    # mess up deposit_index
    deposit.index = state.deposit_index + 1

    yield from run_deposit_processing(state, deposit, validator_index, valid=False)


@spec_state_test
def test_bad_merkle_proof(state):
    validator_index = len(state.validator_registry)
    amount = spec.MAX_EFFECTIVE_BALANCE
    deposit = prepare_state_and_deposit(state, validator_index, amount)

    # mess up merkle branch
    deposit.proof[-1] = spec.ZERO_HASH

    yield from run_deposit_processing(state, deposit, validator_index, valid=False)
