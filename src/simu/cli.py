"""Ligne de commande : ``python -m simu run scenario.yaml [--out dossier]``."""

from __future__ import annotations

import argparse
import sys

from simu import scenario, standard


def _fmt(x: float) -> str:
    return f"{x:,.0f}".replace(",", " ")


def main(argv: list[str] | None = None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    parser = argparse.ArgumentParser(prog="simu", description="Simulateur énergie (PV + batterie + marché)")
    sub = parser.add_subparsers(dest="command", required=True)
    run_parser = sub.add_parser("run", help="exécuter un scénario YAML")
    run_parser.add_argument("scenario")
    run_parser.add_argument("--out", help="dossier de sortie : CSV par pas + graphiques PNG")
    run_parser.add_argument("--week", help="début de la semaine affichée dans les graphiques (AAAA-MM-JJ)")
    args = parser.parse_args(argv)

    config = scenario.read(args.scenario)
    res = scenario.run(config)
    _, _, tz = scenario._period(config)
    inputs = res.inputs
    daily = standard.daily_energy_kwh(inputs["load_kw"], tz)
    equipped = res.after is not res.before and (config.get("pv") or config.get("battery"))

    print(f"Période : {inputs.index[0].tz_convert(tz)} -> {inputs.index[-1].tz_convert(tz)} ({len(inputs)} pas de 15 min)")
    print(f"Consommation : {daily.sum():.2f} kWh, soit {daily.mean():.2f} kWh/jour en moyenne")
    if "spot_eur_mwh" in inputs:
        print(f"Spot moyen : {inputs['spot_eur_mwh'].mean():.2f} €/MWh")
    print("Coût sans équipement :")
    for c in res.costs_before:
        extra = ""
        if c.offer == "bloc_spot":
            d = c.details
            extra = f"  (bloc {d['bloc_eur']:.2f} € + spot {d['spot_eur']:+.2f} €)"
        print(f"  {c.offer:<10} {c.total_eur:9.2f} €   {c.eur_per_mwh:7.2f} €/MWh{extra}")

    if equipped:
        s = res.summary_after
        print("Avec équipement :")
        if config.get("pv"):
            print(f"  PV {config['pv']['peak_kw']} kWc : {s['pv_kwh']:.0f} kWh produits, autoconsommation {s['taux_autoconso']:.0%}, "
                  f"autoproduction {s['taux_autoproduction']:.0%}")
        if res.battery:
            print(f"  Batterie {res.battery.capacity_kwh} kWh : {s['decharge_kwh']:.0f} kWh restitués, "
                  f"{s['cycles_equivalents']:.0f} cycles, pertes {s['pertes_batterie_kwh']:.0f} kWh")
        for c0, c1 in zip(res.costs_before, res.costs_after):
            print(f"  {c1.offer:<10} {c1.total_eur:9.2f} €   (gain {c0.total_eur - c1.total_eur:+.2f} €)")
    if res.penalty_before:
        print(f"Pénalités de dépassement : {res.penalty_before['penalite_eur']:.0f} € -> {res.penalty_after['penalite_eur']:.0f} € "
              f"(pointe {res.penalty_before['pointe_kw']:.1f} -> {res.penalty_after['pointe_kw']:.1f} kW)")
    for p in res.profitability:
        payback = "jamais" if p.payback_years == float("inf") else f"{p.payback_years:.1f} ans"
        print(f"Rentabilité (prix {p.level:<6}) : CAPEX {_fmt(p.capex_eur)} €, gain net {_fmt(p.net_annual_eur)} €/an, "
              f"retour {payback}, bilan sur {p.life_years:.0f} ans {_fmt(p.lifetime_balance_eur)} €")

    if args.out:
        csv_path = scenario.export_csv(res, f"{args.out}/resultats.csv")
        figs = scenario.make_plots(res, args.out, args.week)
        print(f"Export : {csv_path} + {len(figs)} graphiques dans {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
