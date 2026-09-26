"""
ORE version 1.8.17.0 adds support for ABOVEPROB and BELOWPROB in the GaussianCam model.
However, an oversight in the underlying getFutureBarrierProb function causes both functions
to return only 0 or 1 when the FX rate's source currency matches the model's base currency.

As a result, if ABOVEPROB or BELOWPROB is used to implement an FX barrier option,
with EUR-GBP as the underlying and American barrier, the barrier will effectively 
act like an European one when EUR is the base currency of the GaussianCam model.

This behaviour is demonstrated by this scripts. It computes the NPV of two fx barrier options
with the help of the GaussianCam model. The two options have EUR-GBP as underlying and
only differ from each other in the way how the barrier is monitored, i.e., American vs European.
Afterwards the script checks whether the NPVs are equal. The whole procedure is repeated twice,
once with GBP and once with EUR as base currency. 

Using the version v1.8.17.0, it can be observed that the option prices are
unexpectedly identical when EUR is the base currency. Use the fixed version
provided by this branch shows that the option prices are different independently
of the base currency.

Usage:
    python run.py /path/to/ORE/executable

Technical details:
The incorrect behavior of 'ABOVEPROB' / 'BELOWPROB' can be fixed by adding the missing case:
    (ind1 == Null<Size>() && ind2 != Null<Size>())
inside the function 'getFutureBarrierProb', see the lines 879-903 of the file
    "engine/OREData/ored/scripting/models/gaussiancam.cpp"
Due to this missing case, the variance used for the computation of the
barrier hit probability remains zero.
"""

import argparse
import csv
import os
import shutil
import subprocess
import sys

CONTINUOUS, DISCRETE = "FX_BARRIER_CONTINUOUS", "FX_BARRIER_DISCRETE"

RUNS = [
    ("GBP", "Input/ore_base_gbp.xml"),
    ("EUR", "Input/ore_base_eur.xml"),
]


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("ore_exe", help="path to a compiled `ore` executable")
    return parser.parse_args()


def resolve_ore(ore_exe):
    resolved = shutil.which(ore_exe)
    if resolved is None:
        sys.exit(f"ORE executable not found or not executable: {ore_exe}")
    resolved = os.path.abspath(resolved)
    print(f"Using ORE executable: {resolved}")
    return resolved


def npvs(folder):
    with open(os.path.join(folder, "npv.csv")) as f:
        rows = [r for r in csv.reader(f) if r and not r[0].startswith("#")]
    return {r[0]: (r[4], r[5]) for r in rows}


def main():
    ore_exe = resolve_ore(parse_args().ore_exe)
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    for base, config in RUNS:
        print(f"\n=== Pricing with the model based in {base} ({config}) ===")
        if subprocess.call([ore_exe, config]) != 0:
            sys.exit(f"ORE failed on {config}")

    print()
    print("=" * 78)
    print(" American vs discrete European monitoring:")
    print("=" * 78)

    verdicts = []

    for base, _ in RUNS:
        folder = os.path.join("Output", "base_" + base)
        npv = npvs(folder)
        identical = npv[CONTINUOUS][0] == npv[DISCRETE][0]
        verdicts.append((base, identical))
        print()

        print(f" model base {base} --------------------")
        for label, trade in (("continuous (American)", CONTINUOUS),
                             ("discrete   (European) ", DISCRETE)):
            value, ccy = npv[trade]
            print(f"   {label}   NPV = {float(value):13.6f} {ccy}")
        if identical:
            print(" -> American Monitoring has been silently reduced to European monitoring!")
        else:
            print(" -> NPVs for American and European monitoring are different as expected.")

if __name__ == "__main__":
    sys.exit(main())
