#!/usr/bin/env python3

import re
import subprocess
import tempfile
from pathlib import Path


WORKDIR = Path(__file__).resolve().parent
STATE_TEMPLATE = WORKDIR / "biquad.in"
REACTIONS = WORKDIR / "biquad.r"
DEFAULT_INPUTS = [100, 5, 500, 20, 250]


def read_template(path: Path):
    species = []
    counts = {}
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        name, quantity, _ = line.split()
        species.append(name)
        counts[name] = int(quantity)
    return species, counts


def write_state(path: Path, species, counts):
    lines = [f"{name} {counts[name]} N" for name in species]
    path.write_text("\n".join(lines) + "\n")


def run_cycle(species, template_counts, x_value, x_feedback, b1_state, b2_state):
    counts = dict(template_counts)
    counts["X"] = x_value + x_feedback
    counts["B1"] = b1_state
    counts["B2"] = b2_state
    counts["Y"] = 0

    with tempfile.NamedTemporaryFile("w", suffix=".in", dir="/tmp", delete=False) as handle:
        state_path = Path(handle.name)
    write_state(state_path, species, counts)

    proc = subprocess.run(
        ["./aleae", str(state_path), str(REACTIONS), "1", "-1", "0"],
        cwd=WORKDIR,
        text=True,
        capture_output=True,
        check=True,
    )

    match = re.search(r"avg \[(.*)\]", proc.stdout)
    if not match:
        raise RuntimeError("Could not parse Aleae output")

    values = [int(round(float(token.strip()))) for token in match.group(1).split(",")]
    final_counts = dict(zip(species, values))
    return {
        "loaded_X": counts["X"],
        "Y": final_counts["Y"],
        "X_next": final_counts["Xn"],
        "B1_next": final_counts["B1n"],
        "B2_next": final_counts["B2n"],
    }


def main():
    species, template_counts = read_template(STATE_TEMPLATE)

    x_feedback = 0
    b1_state = 0
    b2_state = 0
    outputs = []

    for cycle, value in enumerate(DEFAULT_INPUTS, start=1):
        result = run_cycle(species, template_counts, value, x_feedback, b1_state, b2_state)
        outputs.append(result["Y"])
        print(
            f"cycle {cycle}: input={value}, loaded_X={result['loaded_X']}, "
            f"Y={result['Y']}, next=(X={result['X_next']}, B1={result['B1_next']}, B2={result['B2_next']})"
        )
        x_feedback = result["X_next"]
        b1_state = result["B1_next"]
        b2_state = result["B2_next"]

    print(outputs)


if __name__ == "__main__":
    main()
