from pasiphae.tools import with_last


def test_with_last_works_for_empty_table():
    assert list(with_last([])) == []


def test_with_last_will_be_corect_for_sigle_item():
    assert list(with_last([1])) == [(1, True)]


def test_with_last_will_be_corect_for_multiple_items():
    assert list(with_last([1, 2, 3])) == [(1, False), (2, False), (3, True)]
