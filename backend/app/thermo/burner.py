"""Graphical burner start/stop physics.

24 gas burners, 40 MW thermal each (960 MW total), arranged in three levels
on the front and rear boiler walls:

    Level A at  9 m: front FA1-FA4, rear RA1-RA4
    Level B at 12 m: front FB1-FB4, rear RB1-RB4
    Level C at 15 m: front FC1-FC4, rear RC1-RC4

Each burner ramps linearly towards its target load over its own ramp time.
The gas-side heat reaching the platen is a fraction of the burner heat, delayed
by the furnace gas residence time:

    Q_burners(t)   = sum_i 40 MW * load_i(t)
    Q_gas(t)       = q_platen_fraction * Q_burners(t - gas_to_metal_lag_s)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Iterable

from app.core.errors import DomainError

BURNER_RATED_MW = 40.0
LEVEL_ELEVATION_M = {"A": 9.0, "B": 12.0, "C": 15.0}
BOILER_WIDTH_M = 20.0
DEFAULT_Q_PLATEN_FRACTION = 0.15
DEFAULT_GAS_LAG_S = 5.0
DEFAULT_TARGET_LOAD = 1.0
DEFAULT_RAMP_TIME_S = 30.0


@dataclass(frozen=True)
class BurnerSpec:
    """Static description of one gas burner."""

    tag: str
    level: str
    row: str  # "front" | "rear"
    index: int  # 1..4 from left to right
    elevation_m: float
    lateral_m: float
    rated_MW: float = BURNER_RATED_MW

    def as_dict(self) -> dict:
        return {
            "tag": self.tag,
            "level": self.level,
            "row": self.row,
            "index": self.index,
            "elevation_m": self.elevation_m,
            "lateral_m": self.lateral_m,
            "rated_MW": self.rated_MW,
        }


def build_burners() -> list[BurnerSpec]:
    """Build the fixed 24-burner layout."""
    burners: list[BurnerSpec] = []
    for level, elevation in LEVEL_ELEVATION_M.items():
        for row, prefix in (("front", "F"), ("rear", "R")):
            for index in range(1, 5):
                burners.append(
                    BurnerSpec(
                        tag=f"{prefix}{level}{index}",
                        level=level,
                        row=row,
                        index=index,
                        elevation_m=elevation,
                        lateral_m=(index - 0.5) * BOILER_WIDTH_M / 4.0,
                    )
                )
    return burners


BURNERS: list[BurnerSpec] = build_burners()
BURNER_BY_TAG: dict[str, BurnerSpec] = {b.tag: b for b in BURNERS}
BURNER_TAGS: tuple[str, ...] = tuple(b.tag for b in BURNERS)


@dataclass(frozen=True)
class BurnerEvent:
    """One ignition or shutdown command."""

    tag: str
    time_s: float
    state: str = "on"  # "on" | "off"
    target_load_fraction: float = DEFAULT_TARGET_LOAD
    ramp_time_s: float = DEFAULT_RAMP_TIME_S

    def __post_init__(self) -> None:
        if self.tag not in BURNER_BY_TAG:
            raise DomainError("unknown_burner", context={"tag": self.tag})
        if self.state not in ("on", "off"):
            raise DomainError(
                "out_of_envelope",
                "Burner state must be 'on' or 'off'.",
                "\u0648\u0636\u0639\u06cc\u062a \u0634\u0631\u0639\u200c\u06a9\u0646 \u0628\u0627\u06cc\u062f on \u06cc\u0627 off \u0628\u0627\u0634\u062f.",
                context={"tag": self.tag, "state": self.state},
            )
        if not (0.0 <= self.target_load_fraction <= 1.0):
            raise DomainError(
                "out_of_envelope",
                "Target load fraction must lie between 0 and 1.",
                "\u06a9\u0633\u0631 \u0628\u0627\u0631 \u0647\u062f\u0641 \u0628\u0627\u06cc\u062f \u0628\u06cc\u0646 0 \u0648 1 \u0628\u0627\u0634\u062f.",
                context={"tag": self.tag, "target_load_fraction": self.target_load_fraction},
            )
        if self.time_s < 0 or self.ramp_time_s < 0:
            raise DomainError("invalid_dt", context={"time_s": self.time_s, "ramp_time_s": self.ramp_time_s})

    @property
    def effective_load(self) -> float:
        """Target load actually demanded by this event."""
        return self.target_load_fraction if self.state == "on" else 0.0

    def as_dict(self) -> dict:
        spec = BURNER_BY_TAG[self.tag]
        return {
            "tag": self.tag,
            "level": spec.level,
            "row": spec.row,
            "time_s": self.time_s,
            "state": self.state,
            "target_load_fraction": self.effective_load,
            "ramp_time_s": self.ramp_time_s,
        }


@dataclass
class BurnerSchedule:
    """A time-ordered set of burner events."""

    events: list[BurnerEvent] = field(default_factory=list)
    rated_MW: float = BURNER_RATED_MW

    def __post_init__(self) -> None:
        self.events.sort(key=lambda e: e.time_s)

    def add(self, event: BurnerEvent) -> None:
        """Insert an event keeping the schedule ordered."""
        self.events.append(event)
        self.events.sort(key=lambda e: e.time_s)

    def events_of(self, tag: str) -> list[BurnerEvent]:
        return [e for e in self.events if e.tag == tag]

    def load_of(self, tag: str, time_s: float) -> float:
        """Burner load fraction at ``time_s`` following the ramp segments."""
        if tag not in BURNER_BY_TAG:
            raise DomainError("unknown_burner", context={"tag": tag})
        load = 0.0
        for event in self.events_of(tag):
            if time_s < event.time_s:
                break
            target = event.effective_load
            if event.ramp_time_s <= 0 or time_s >= event.time_s + event.ramp_time_s:
                load = target
            else:
                progress = (time_s - event.time_s) / event.ramp_time_s
                return load + (target - load) * progress
        return load

    def q_burners_mw(self, time_s: float) -> float:
        """Total fired heat [MW] at ``time_s``."""
        return sum(
            self.rated_MW * self.load_of(b.tag, time_s) for b in BURNERS
        )

    def active_count(self, time_s: float) -> int:
        """Number of burners with a non-zero load at ``time_s``."""
        return sum(1 for b in BURNERS if self.load_of(b.tag, time_s) > 1e-9)

    def states_at(self, time_s: float) -> dict[str, float]:
        """Load fraction of every burner at ``time_s``."""
        return {b.tag: self.load_of(b.tag, time_s) for b in BURNERS}


def as_schedule(events: Iterable[BurnerEvent | dict]) -> BurnerSchedule:
    """Build a schedule from dataclasses or plain dictionaries."""
    schedule = BurnerSchedule()
    for item in events:
        if isinstance(item, BurnerEvent):
            schedule.add(item)
        else:
            schedule.add(
                BurnerEvent(
                    tag=item["tag"],
                    time_s=float(item.get("time_s", item.get("ignition_time_s", 0.0))),
                    state=item.get("state", "on"),
                    target_load_fraction=float(
                        item.get("target_load_fraction", DEFAULT_TARGET_LOAD)
                    ),
                    ramp_time_s=float(item.get("ramp_time_s", DEFAULT_RAMP_TIME_S)),
                )
            )
    return schedule


def q_burners_of_t(schedule: BurnerSchedule | Iterable[BurnerEvent | dict]) -> Callable[[float], float]:
    """Return Q_burners(t) [MW] for a schedule."""
    prepared = schedule if isinstance(schedule, BurnerSchedule) else as_schedule(schedule)
    return lambda t: prepared.q_burners_mw(t)


def q_gas_to_platen_of_t(
    schedule: BurnerSchedule | Iterable[BurnerEvent | dict],
    q_fraction: float = DEFAULT_Q_PLATEN_FRACTION,
    lag_s: float = DEFAULT_GAS_LAG_S,
) -> Callable[[float], float]:
    """Return Q_gas(t) [MW] reaching the platen, delayed by ``lag_s`` seconds."""
    if not (0.0 <= q_fraction <= 1.0):
        raise DomainError(
            "out_of_envelope",
            "q_platen_fraction must lie between 0 and 1.",
            "\u06a9\u0633\u0631 \u062d\u0631\u0627\u0631\u062a \u067e\u0644\u06cc\u062a\u0646 \u0628\u0627\u06cc\u062f \u0628\u06cc\u0646 0 \u0648 1 \u0628\u0627\u0634\u062f.",
            context={"q_platen_fraction": q_fraction},
        )
    if lag_s < 0:
        raise DomainError("invalid_dt", context={"gas_to_metal_lag_s": lag_s})
    prepared = schedule if isinstance(schedule, BurnerSchedule) else as_schedule(schedule)
    return lambda t: q_fraction * prepared.q_burners_mw(t - lag_s)


def preset_schedule(name: str) -> list[BurnerEvent]:
    """Named start-up presets used by the Android burner screen."""
    normalized = name.strip().lower().replace(" ", "_").replace("-", "_")
    events: list[BurnerEvent] = []
    if normalized in ("cold_start", "cold"):
        for level, delay in (("A", 0.0), ("B", 300.0), ("C", 600.0)):
            for row in ("F", "R"):
                for index in range(1, 5):
                    events.append(
                        BurnerEvent(f"{row}{level}{index}", delay, "on", 1.0, 60.0)
                    )
    elif normalized in ("warm_start", "warm"):
        for level, delay in (("A", 0.0), ("B", 0.0), ("C", 240.0)):
            for row in ("F", "R"):
                for index in range(1, 5):
                    events.append(
                        BurnerEvent(f"{row}{level}{index}", delay, "on", 1.0, 30.0)
                    )
    elif normalized in ("level_a", "level_a_only"):
        for row in ("F", "R"):
            for index in range(1, 5):
                events.append(BurnerEvent(f"{row}A{index}", 0.0, "on", 1.0, 30.0))
    elif normalized in ("all_on", "all"):
        for tag in BURNER_TAGS:
            events.append(BurnerEvent(tag, 0.0, "on", 1.0, 30.0))
    elif normalized in ("all_off", "reset"):
        for tag in BURNER_TAGS:
            events.append(BurnerEvent(tag, 0.0, "off", 0.0, 30.0))
    elif normalized in ("cold_start_4", "four_burners"):
        for index in range(1, 5):
            events.append(BurnerEvent(f"FA{index}", 0.0, "on", 1.0, 30.0))
    else:
        raise DomainError(
            "out_of_envelope",
            "Unknown burner preset.",
            "\u067e\u06cc\u0634\u200c\u062a\u0646\u0638\u06cc\u0645 \u0634\u0631\u0639\u200c\u06a9\u0646 \u0646\u0627\u0634\u0646\u0627\u062e\u062a\u0647 \u0627\u0633\u062a.",
            context={"preset": name},
        )
    events.sort(key=lambda e: (e.time_s, e.tag))
    return events


PRESETS: tuple[tuple[str, str, str], ...] = (
    ("cold_start", "Cold start (A \u2192 B \u2192 C)", "\u0634\u0631\u0648\u0639 \u0633\u0631\u062f (\u06a9\u0646\u062f\u0647 \u2192 \u0628\u06cc\u0646\u0627\u0628\u06cc\u0644 \u2192 \u0646\u0648\u0627\u062d\u06cc)"),
    ("warm_start", "Warm start", "\u0634\u0631\u0648\u0639 \u06af\u0631\u0645"),
    ("level_a", "Level A only", "\u0641\u0642\u0637 \u0633\u0637\u062d A"),
    ("all_on", "All ON", "\u0647\u0645\u0647 \u0631\u0648\u0634\u0646"),
    ("all_off", "All OFF", "\u0647\u0645\u0647 \u062e\u0627\u0645\u0648\u0634"),
    ("reset", "Reset", "\u0628\u0627\u0632\u0646\u0634\u0627\u0646\u06cc"),
)


def preset_catalog() -> list[dict]:
    """Preset descriptions for the UI, in English and Persian."""
    return [
        {
            "id": preset_id,
            "event_count": len(preset_schedule(preset_id)),
            "label_en": label_en,
            "label_fa": label_fa,
        }
        for preset_id, label_en, label_fa in PRESETS
    ]
