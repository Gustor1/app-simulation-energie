"""Ligne de commande : ``python -m simu run scenario.yaml``."""

from __future__ import annotations

import argparse

from simu import scenario, standard


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="simu", description="Simulateur énergie (PV + batterie + marché)")
    sub = parser.add_subparsers(dest="command", required=True)
    run_parser = sub.add_parser("run", help="exécuter un scénario YAML")
    run_parser.add_argument("scenario")
    args = parser.parse_args(argv)

    config = scenario.read(args.scenario)
    inputs, costs = scenario.run(config)
    _, _, tz = scenario._period(config)
    daily = standard.daily_energy_kwh(inputs["load_kw"], tz)

    print(f"Période : {inputs.index[0].tz_convert(tz)} -> {inputs.index[-1].tz_convert(tz)} ({len(inputs)} pas de 15 min)")
    print(f"Consommation : {daily.sum():.2f} kWh, soit {daily.mean():.2f} kWh/jour en moyenne")
    if "spot_eur_mwh" in inputs:
        print(f"Spot moyen : {inputs['spot_eur_mwh'].mean():.2f} €/MWh")
    print("Coût sans équipement :")
    for c in costs:
        extra = ""
        if c.offer == "bloc_spot":
            d = c.details
            extra = f"  (bloc {d['bloc_eur']:.2f} € + spot {d['spot_eur']:+.2f} €)"
        print(f"  {c.offer:<10} {c.total_eur:9.2f} €   {c.eur_per_mwh:7.2f} €/MWh{extra}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
