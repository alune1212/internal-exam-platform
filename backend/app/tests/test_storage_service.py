from types import SimpleNamespace

import pytest
from sqlalchemy.orm import Session

from app.core.config import settings
from app.services import storage_service


def test_storage_reserve_uses_stricter_twenty_gib_or_three_times_footprint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "storage_min_free_bytes", 20 * 1024**3)
    monkeypatch.setattr(settings, "storage_footprint_multiplier", 3)

    minimum_dominates = storage_service.calculate_storage_reserve(
        free_bytes=25 * 1024**3,
        database_bytes=1024**3,
        media_bytes=1024**3,
        proposed_bytes=1024**3,
    )
    footprint_dominates = storage_service.calculate_storage_reserve(
        free_bytes=40 * 1024**3,
        database_bytes=5 * 1024**3,
        media_bytes=5 * 1024**3,
        proposed_bytes=2 * 1024**3,
    )

    assert minimum_dominates.required_free_bytes == 20 * 1024**3
    assert minimum_dominates.sufficient is True
    assert footprint_dominates.required_free_bytes == 36 * 1024**3
    assert footprint_dominates.free_after_bytes == 38 * 1024**3
    assert footprint_dominates.sufficient is True


def test_storage_reserve_rejects_upload_without_affecting_answer_services(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        storage_service.shutil,
        "disk_usage",
        lambda _path: SimpleNamespace(free=10),
    )
    monkeypatch.setattr(storage_service, "database_footprint_bytes", lambda _db: 4)
    monkeypatch.setattr(storage_service, "media_footprint_bytes", lambda: 3)
    monkeypatch.setattr(settings, "storage_min_free_bytes", 8)
    monkeypatch.setattr(settings, "storage_footprint_multiplier", 3)

    with pytest.raises(storage_service.StorageReserveError):
        storage_service.assert_storage_reserve(db, proposed_bytes=2)

    result = storage_service.get_storage_reserve(db, proposed_bytes=0)
    assert result.sufficient is False
    assert result.required_free_bytes == 21
