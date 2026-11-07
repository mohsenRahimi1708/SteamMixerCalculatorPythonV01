"""Burner layout, schedule and delayed gas heat tests."""

from __future__ import annotations

import pytest

from app.core.errors import DomainError
from app.thermo import burner as burner_mod


def test_layout_has_24_burners_on_three_levels():
    """3 levels x 2 rows x 4 burners, with the documented elevations and tags."""
    assert len(burner_mod.BURNERS) == 24
    assert len(burner_mod.BURNER_TAGS) == 24
    for level, elevation in (("A", 9.0), ("B", 12.0), ("C", 15.0)):
        level_burners = [b for b in burner_mod.BURNERS if b.level == level]
        assert len(level_burners) == 8
        assert all(b.elevation_m == pytest.approx(elevation) for b in level_burners)
    assert burner_mod.BURNER_BY_TAG["FA1"].row == "front"
    assert burner_mod.BURNER_BY_TAG["RC4"].row == "rear"
    assert sum(b.rated_MW for b in burner_mod.BURNERS) == pytest.approx(960.0)


def test_burners_are_equally_spaced_across_the_width():
    """Lateral positions are 2.5, 7.5, 12.5 and 17.5 m across the 20 m width."""
    front = [burner_mod.BURNER_BY_TAG[f"FA{i}"] for i in range(1, 5)]
    assert [b.lateral_m for b in front] == pytest.approx([2.5, 7.5, 12.5, 17.5])


def test_ramp_reaches_the_target_load():
    """A 30 s ramp from cold reaches 160 MW after 30 s for four burners."""
    schedule = burner_mod.as_schedule(burner_mod.preset_schedule("four_burners"))
    assert schedule.q_burners_mw(0.0) == pytest.approx(0.0)
    assert schedule.q_burners_mw(15.0) == pytest.approx(80.0, rel=1e-6)
    assert schedule.q_burners_mw(30.0) == pytest.approx(160.0)
    assert schedule.q_burners_mw(120.0) == pytest.approx(160.0)


def test_shutdown_ramps_back_to_zero():
    """An OFF command ramps the burner down over its ramp time."""
    schedule = burner_mod.BurnerSchedule()
    schedule.add(burner_mod.BurnerEvent("FA1", 0.0, "on", 1.0, 0.0))
    schedule.add(burner_mod.BurnerEvent("FA1", 60.0, "off", 0.0, 20.0))
    assert schedule.q_burners_mw(59.0) == pytest.approx(40.0)
    assert schedule.q_burners_mw(70.0) == pytest.approx(20.0)
    assert schedule.q_burners_mw(80.0) == pytest.approx(0.0)
    assert schedule.active_count(90.0) == 0


def test_partial_load_is_respected():
    """A 50 % target load fires 20 MW."""
    schedule = burner_mod.as_schedule(
        [{"tag": "FB2", "time_s": 0.0, "target_load_fraction": 0.5, "ramp_time_s": 0.0}]
    )
    assert schedule.q_burners_mw(1.0) == pytest.approx(20.0)


def test_gas_transport_delay():
    """Q_gas(t) = fraction * Q_burners(t - lag)."""
    schedule = burner_mod.as_schedule(burner_mod.preset_schedule("four_burners"))
    q_gas = burner_mod.q_gas_to_platen_of_t(schedule, q_fraction=0.15, lag_s=5.0)
    assert q_gas(3.0) == pytest.approx(0.0)
    assert q_gas(10.0) == pytest.approx(0.15 * 160.0 * (5.0 / 30.0), rel=1e-6)
    assert q_gas(60.0) == pytest.approx(24.0)


def test_presets_are_valid():
    """Every advertised preset must build a valid schedule."""
    for preset in burner_mod.PRESETS:
        events = burner_mod.preset_schedule(preset[0])
        assert events, preset[0]
        assert all(event.tag in burner_mod.BURNER_BY_TAG for event in events)
    cold = burner_mod.preset_schedule("cold_start")
    assert {event.time_s for event in cold} == {0.0, 300.0, 600.0}


def test_unknown_burner_and_preset_are_rejected():
    """Unknown tags and presets are client errors."""
    with pytest.raises(DomainError):
        burner_mod.BurnerEvent("XA9", 0.0)
    with pytest.raises(DomainError):
        burner_mod.preset_schedule("nope")


def test_invalid_load_fraction_is_rejected():
    """Load fractions outside 0..1 are rejected."""
    with pytest.raises(DomainError):
        burner_mod.BurnerEvent("FA1", 0.0, target_load_fraction=1.5)
    with pytest.raises(DomainError):
        burner_mod.q_gas_to_platen_of_t([], q_fraction=2.0)
