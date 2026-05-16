from tinyvm.data.emit import _row_seed


def test_row_seed_is_deterministic():
    assert _row_seed(0, "train", None, 0) == _row_seed(0, "train", None, 0)


def test_row_seed_changes_with_seed_base():
    assert _row_seed(0, "train", None, 0) != _row_seed(1, "train", None, 0)


def test_row_seed_changes_with_split():
    assert _row_seed(0, "train", None, 0) != _row_seed(0, "eval", None, 0)


def test_row_seed_changes_with_bucket():
    assert _row_seed(0, "eval", "len_8", 0) != _row_seed(0, "eval", "len_16", 0)


def test_row_seed_changes_with_index():
    assert _row_seed(0, "train", None, 0) != _row_seed(0, "train", None, 1)


def test_row_seed_is_64_bit_unsigned_int():
    s = _row_seed(0, "train", None, 0)
    assert isinstance(s, int)
    assert 0 <= s < 2**64
