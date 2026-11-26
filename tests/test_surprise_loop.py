"""Regression tests for surprise promotion tag semantics."""


def test_non_big_surprise_has_one_surprise_tag():
    from theory_x.life.surprise_loop import _surprise_tags
    assert _surprise_tags(False) == ["surprise"]


def test_big_surprise_has_both_distinct_tags():
    from theory_x.life.surprise_loop import _surprise_tags
    tags = _surprise_tags(True)
    assert tags == ["surprise", "big_surprise"]
    assert len(tags) == len(set(tags))
