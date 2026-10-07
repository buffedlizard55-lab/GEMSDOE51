from gems51.uniqueness import known_prior_label


def test_known_prior_full_fingerprint_matches_exactly():
    fingerprint = "c55bafc470054e8271dcb89347a17e07fefe50de6af6e6ba6c4b169ef7ab6fa9"
    assert known_prior_label(fingerprint) == "GEMSDOE32 H33-2-B2 (zero-outside prior)"
    changed = fingerprint[:-1] + ("0" if fingerprint[-1] != "0" else "1")
    assert known_prior_label(changed) is None


def test_truncated_historical_fingerprint_is_matched_as_prefix():
    fingerprint = "baeae3219bba6a19"
    full_digest = fingerprint + "0" * (64 - len(fingerprint))
    assert known_prior_label(full_digest) == "GEMSDOE32 H33-2-B2 (NaN twin prior)"


def test_unlisted_fingerprint_does_not_match():
    assert known_prior_label("0" * 64) is None
