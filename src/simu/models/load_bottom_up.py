"""Courbe de charge bottom-up : somme d'appareils, avec une part d'aléa.

Simulation à la minute (heure locale), puis moyenne au pas de 15 min (format standard).

Types d'appareils :
- ``cyclic``    : cycles réguliers (ex. réfrigérateur : 400 W, 7 min, 2×/h) ; aléa = instant
                  de démarrage de chaque cycle dans sa fenêtre (60 / cycles_par_heure minutes).
- ``schedule``  : marche fixe sur des plages horaires (ex. TV 18 h–23 h).
- ``daily_run`` : une marche par jour de durée fixe (ex. lave-linge 2 h) ; aléa = heure de
                  démarrage, tirée uniformément pour que la marche tienne dans [earliest_h, latest_end_h].
- ``heating``   : E_jour = k × (consigne − T_moyenne_jour) si T_moyenne_jour < seuil, sinon 0 ;
                  puissance constante sur la journée.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from simu import standard


@dataclass
class Cyclic:
    name: str
    power_w: float
    on_minutes: int
    cycles_per_hour: int

    def minutes_w(self, clock: pd.DatetimeIndex, rng: np.random.Generator) -> np.ndarray:
        slot = 60 // self.cycles_per_hour
        if self.on_minutes > slot:
            raise ValueError(f"{self.name} : {self.on_minutes} min de marche > fenêtre de {slot} min")
        n = len(clock)
        n_slots = -(-n // slot)
        offsets = rng.integers(0, slot - self.on_minutes + 1, size=n_slots)
        minute_in_slot = np.arange(n) % slot
        start = offsets[np.arange(n) // slot]
        on = (minute_in_slot >= start) & (minute_in_slot < start + self.on_minutes)
        return on * float(self.power_w)


@dataclass
class Schedule:
    name: str
    power_w: float
    windows: list[tuple[float, float]]  # [(début_h, fin_h), ...] en heure locale, fin exclue

    def minutes_w(self, clock: pd.DatetimeIndex, rng: np.random.Generator) -> np.ndarray:
        hour = clock.hour + clock.minute / 60
        on = np.zeros(len(clock), dtype=bool)
        for h0, h1 in self.windows:
            on |= (hour >= h0) & (hour < h1)
        return on * float(self.power_w)


@dataclass
class DailyRun:
    name: str
    power_w: float
    duration_h: float
    earliest_h: float = 0.0
    latest_end_h: float = 24.0

    def minutes_w(self, clock: pd.DatetimeIndex, rng: np.random.Generator) -> np.ndarray:
        duration_min = round(self.duration_h * 60)
        first, last = round(self.earliest_h * 60), round(self.latest_end_h * 60) - duration_min
        if last < first:
            raise ValueError(f"{self.name} : la marche de {self.duration_h} h ne tient pas dans la plage")
        minute_of_day = clock.hour * 60 + clock.minute
        days = clock.normalize()
        out = np.zeros(len(clock))
        for day in days.unique():
            start = rng.integers(first, last + 1)
            mask = (days == day) & (minute_of_day >= start) & (minute_of_day < start + duration_min)
            out[mask] = self.power_w
        return out


@dataclass
class Heating:
    name: str
    k_kwh_per_degc: float  # kWh par jour et par °C d'écart
    temperatures: float | dict = 20.0  # T moyenne journalière (°C) : constante ou {date: T}
    setpoint_c: float = 20.0
    threshold_c: float = 15.0

    def daily_kwh(self, t_mean: float) -> float:
        return self.k_kwh_per_degc * (self.setpoint_c - t_mean) if t_mean < self.threshold_c else 0.0

    def minutes_w(self, clock: pd.DatetimeIndex, rng: np.random.Generator) -> np.ndarray:
        days = clock.normalize()
        out = np.zeros(len(clock))
        for day in days.unique():
            if isinstance(self.temperatures, dict):
                key = pd.Timestamp(day).date()
                temps = {pd.Timestamp(k).date(): v for k, v in self.temperatures.items()}
                if key not in temps:
                    raise KeyError(f"{self.name} : température manquante pour le {key}")
                t_mean = float(temps[key])
            else:
                t_mean = float(self.temperatures)
            mask = days == day
            hours_in_day = mask.sum() / 60  # 23 h ou 25 h les jours de changement d'heure
            out[mask] = self.daily_kwh(t_mean) / hours_in_day * 1000
        return out


APPLIANCE_TYPES = {"cyclic": Cyclic, "schedule": Schedule, "daily_run": DailyRun, "heating": Heating}


def appliance_from_dict(spec: dict):
    spec = dict(spec)
    kind = spec.pop("type")
    if kind not in APPLIANCE_TYPES:
        raise ValueError(f"type d'appareil inconnu {kind!r} ; attendus : {list(APPLIANCE_TYPES)}")
    if "windows" in spec:
        spec["windows"] = [tuple(w) for w in spec["windows"]]
    return APPLIANCE_TYPES[kind](**spec)


def minute_clock(start, end, tz: str) -> pd.DatetimeIndex:
    """Minutes locales du jour ``start`` 00:00 au jour ``end`` inclus."""
    t0 = pd.Timestamp(start).normalize().tz_localize(tz)
    t1 = (pd.Timestamp(end).normalize() + pd.Timedelta(days=1)).tz_localize(tz)
    return pd.date_range(t0, t1, freq="1min", inclusive="left")


def simulate_appliances(appliances, start, end, tz: str = "Europe/Paris", seed: int | None = 0) -> pd.DataFrame:
    """Puissance de chaque appareil (kW), index UTC au pas de 15 min."""
    rng = np.random.default_rng(seed)
    clock = minute_clock(start, end, tz)
    columns = {}
    for appliance in appliances:
        if isinstance(appliance, dict):
            appliance = appliance_from_dict(appliance)
        if appliance.name in columns:
            raise ValueError(f"nom d'appareil en double : {appliance.name}")
        columns[appliance.name] = appliance.minutes_w(clock, rng) / 1000
    minutes = pd.DataFrame(columns, index=clock.tz_convert("UTC"))
    return minutes.resample(standard.FREQ).mean()


def simulate(appliances, start, end, tz: str = "Europe/Paris", seed: int | None = 0) -> pd.DataFrame:
    """Courbe de charge du site au format standard (colonne ``load_kw``)."""
    per_appliance = simulate_appliances(appliances, start, end, tz=tz, seed=seed)
    return standard.validate(per_appliance.sum(axis=1).rename("load_kw").to_frame())
