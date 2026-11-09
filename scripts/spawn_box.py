#!/usr/bin/env python3
"""Spawn a static box obstacle in a running gz sim world.

Asks for the box size and position, then calls the
/world/<world>/create service. Rotation is always (0, 0, 0).

Usage:
    python3 spawn_box.py [--world hippo_world] [--name my_box]
"""
import argparse
import subprocess
import sys
import time


def ask_vec3(prompt):
    """Ask for three floats separated by spaces and/or commas."""
    while True:
        raw = input(prompt).replace(",", " ").split()
        try:
            if len(raw) != 3:
                raise ValueError
            return [float(v) for v in raw]
        except ValueError:
            print("  Please enter exactly three numbers, e.g. '1.1 0.1 2'.")

def ask_vec2(prompt):
    """Ask for two floats separated by spaces and/or commas."""
    while True:
        raw = input(prompt).replace(",", " ").split()
        try:
            if len(raw) != 2:
                raise ValueError
            return [float(v) for v in raw]
        except ValueError:
            print("  Please enter exactly two numbers, e.g. '1.1 0.1'.")


def build_sdf(name, size, pos):
    sx, sy, sz = size
    x, y, z = pos
    geometry = f"<geometry><box><size>{sx} {sy} {sz}</size></box></geometry>"
    return (
        '<sdf version="1.7">'
        f'<model name="{name}">'
        "<static>true</static>"
        f"<pose>{x} {y} {z} 0 0 0</pose>"
        '<link name="link">'
        f'<collision name="collision">{geometry}</collision>'
        f'<visual name="visual">{geometry}</visual>'
        "</link>"
        "</model>"
        "</sdf>"
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--world", default="hippo_world",
                        help="world name (default: hippo_world)")
    parser.add_argument("--name", default=None,
                        help="model name (default: obstacle_box_<timestamp>, must be unique)")
    parser.add_argument("--timeout", type=int, default=2000,
                        help="service timeout in ms (default: 2000)")
    args = parser.parse_args()

    name = args.name or f"obstacle_box_{int(time.time())}"

    try:
        default_size_z = 2.0
        default_pos_z = -0.5
        size_2d = ask_vec2("Size  (x y) [m]: ")
        size = size_2d + [default_size_z]
        pos_2d = ask_vec2("Position (x y) [m]: ")
        pos = pos_2d + [default_pos_z]
    except (EOFError, KeyboardInterrupt):
        print("\nAborted.")
        return 1

    if any(s <= 0 for s in size):
        print("Error: all size values must be positive.")
        return 1

    sdf = build_sdf(name, size, pos)
    # Protobuf text format: the SDF is a string field, so escape the quotes.
    req = 'sdf: "' + sdf.replace('"', '\\"') + '"'

    cmd = [
        "gz", "service",
        "-s", f"/world/{args.world}/create",
        "--reqtype", "gz.msgs.EntityFactory",
        "--reptype", "gz.msgs.Boolean",
        "--timeout", str(args.timeout),
        "--req", req,
    ]

    print(f"Spawning '{name}' with size {size} at {pos} ...")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
    except FileNotFoundError:
        print("Error: 'gz' command not found. Is Gazebo installed and sourced?")
        return 1

    out = (result.stdout + result.stderr).strip()
    if result.returncode == 0 and "true" in out.lower():
        print("Done.")
        return 0

    print("Spawning failed.")
    if out:
        print(out)
    print("Check that the simulation is running, the world name is correct "
          f"('{args.world}'), and that the model name is not already used.")
    return 1


if __name__ == "__main__":
    sys.exit(main())