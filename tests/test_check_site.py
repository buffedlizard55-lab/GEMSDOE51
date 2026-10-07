from pathlib import Path

from scripts import check_site


def test_site_checker_rejects_links_to_archived_candidate_tiff(tmp_path, monkeypatch, capsys):
    root = tmp_path
    docs = root / "docs"
    downloads = docs / "downloads"
    archived = root / "archive" / "submissions" / "2026-10-07" / "old.tif"
    downloads.mkdir(parents=True)
    archived.parent.mkdir(parents=True)
    archived.write_bytes(b"archive-only")
    (docs / "index.html").write_text(
        '<p>No eligible submission file</p>'
        '<a href="../archive/submissions/2026-10-07/old.tif">old</a>'
    )
    (root / "data").mkdir()
    (root / "data" / "submission_manifest.json").write_text(
        '{"status":"NO_ELIGIBLE_CANDIDATE","primary":null}'
    )
    monkeypatch.setattr(check_site, "ROOT", root)
    monkeypatch.setattr(check_site, "DOCS", docs)

    result = check_site.main()

    assert result == 1
    assert "links an archived candidate" in capsys.readouterr().out
