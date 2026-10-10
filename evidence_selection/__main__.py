"""Command-line entry point. Preparing, analyzing, and mock runs never call an API."""

import argparse
import json
from pathlib import Path
import sys
import zipfile

from .analysis import analyze
from .provider import ProviderError
from .runner import prepare, run
from .storage import read_plan, run_lock


def config_for(args):
    if args.config:
        return json.loads(Path(args.config).read_text())
    if (Path(args.output) / "plan.json").exists():
        return read_plan(args.output)["config"]
    return json.loads(Path("configs/pilot.json").read_text())


def export_run(output, destination):
    analyze(output)
    target = Path(destination).resolve()
    directory = Path(output).resolve()
    if target == directory or directory in target.parents:
        raise ValueError("Export destination must be outside the run directory")
    if target.exists():
        raise ValueError("Export destination already exists; choose another filename")
    target.parent.mkdir(parents=True, exist_ok=True)
    with run_lock(directory):
        with zipfile.ZipFile(target, "x", zipfile.ZIP_DEFLATED) as archive:
            for file in sorted(directory.rglob("*")):
                if file.is_file() and file.suffix in (".json", ".md", ".csv"):
                    archive.write(file, str(Path(directory.name) / file.relative_to(directory)))
    return {"exported": str(target)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("prepare", "run", "analyze", "export"):
        command = commands.add_parser(name)
        command.add_argument("--output", required=True)
        if name in ("prepare", "run"):
            command.add_argument("--config")
        if name == "run":
            command.add_argument("--max-calls", type=int)
            command.add_argument("--mock", action="store_true")
            command.add_argument("--retry-uncertain", action="store_true")
        if name == "export":
            command.add_argument("--destination", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "prepare":
            result = prepare(config_for(args), args.output)
        elif args.command == "run":
            result = run(config_for(args), args.output, args.max_calls,
                         args.mock, args.retry_uncertain)
            analysis = analyze(args.output)
            result["decision"] = analysis["decision"]
        elif args.command == "analyze":
            result = analyze(args.output)
        else:
            result = export_run(args.output, args.destination)
        print(json.dumps(result, indent=2, allow_nan=False))
        return 0
    except (ValueError, OSError, ProviderError) as exc:
        print("Error: " + str(exc), file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("\nInterrupted. Checkpoints are retained. An in-flight attempt may need "
              "--retry-uncertain on resume.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
