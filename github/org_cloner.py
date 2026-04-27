"""CLI entry point for the GitHub organisation repository cloner."""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path

if sys.version_info < (3, 10):
    sys.stderr.write(
        f"Error: Python 3.10 or greater is required. Running {sys.version}.\n"
    )
    sys.exit(1)

from github.cloner import build_summary, format_summary, sync_organisation
from github.exclusion import build_rules
from github.github_client import resolve_token

logger = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    """Build and return the argument parser for github-org-cloner."""
    parser = argparse.ArgumentParser(
        prog="github-org-cloner",
        description=(
            "Synchronise all repositories of a GitHub organisation "
            "to a local directory."
        ),
    )
    parser.add_argument(
        "org",
        metavar="ORG",
        help="GitHub organisation login name (e.g. my-company).",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        metavar="DIR",
        type=Path,
        default=None,
        help="Target directory. Defaults to ./<ORG> in the current working directory.",
    )
    parser.add_argument(
        "--exclude-prefix",
        metavar="PREFIX",
        dest="exclude_prefixes",
        action="append",
        default=[],
        help="Exclude repositories whose names start with PREFIX. Repeatable.",
    )
    parser.add_argument(
        "--exclude-suffix",
        metavar="SUFFIX",
        dest="exclude_suffixes",
        action="append",
        default=[],
        help="Exclude repositories whose names end with SUFFIX. Repeatable.",
    )
    parser.add_argument(
        "--exclude",
        metavar="NAME",
        dest="exclude_names",
        action="append",
        default=[],
        help="Exclude a repository by its exact name. Repeatable.",
    )
    parser.add_argument(
        "--exclude-pattern",
        metavar="PATTERN",
        dest="exclude_patterns",
        action="append",
        default=[],
        help="Exclude repositories matching a glob pattern (* and ?). Repeatable.",
    )
    parser.add_argument(
        "--protocol",
        choices=["https", "ssh"],
        default="https",
        help="Clone URL protocol to use. Default: https.",
    )
    parser.add_argument(
        "--max-concurrent",
        metavar="N",
        type=_positive_int_max_50,
        default=5,
        help="Maximum number of parallel git operations (1–50). Default: 5.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Stream per-repository status and enable DEBUG logging.",
    )
    return parser


def _positive_int_max_50(value: str) -> int:
    """Validate that value is an integer in the range 1–50."""
    try:
        int_value = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"'{value}' is not a valid integer.")
    if not (1 <= int_value <= 50):
        raise argparse.ArgumentTypeError(
            f"--max-concurrent must be between 1 and 50, got {int_value}."
        )
    return int_value


def _configure_logging(verbose: bool) -> None:
    """Configure logging for the tool.

    The root logger is set to WARNING to suppress noise from third-party
    libraries. The github package logger is set to DEBUG (verbose) or INFO
    (default), with a clean message-only format so summary output is readable.
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.WARNING)

    github_logger = logging.getLogger("github")
    github_logger.setLevel(logging.DEBUG if verbose else logging.INFO)

    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter("%(message)s"))
    github_logger.addHandler(handler)
    github_logger.propagate = False


def main() -> None:
    """Parse arguments and run the organisation sync."""
    parser = build_parser()
    args = parser.parse_args()

    _configure_logging(verbose=args.verbose)

    token = resolve_token()

    output_dir: Path = (
        args.output_dir if args.output_dir is not None else Path(args.org)
    )
    output_dir = output_dir.resolve()

    rules = build_rules(
        prefixes=args.exclude_prefixes,
        suffixes=args.exclude_suffixes,
        names=args.exclude_names,
        patterns=args.exclude_patterns,
    )

    results = asyncio.run(
        sync_organisation(
            org=args.org,
            target_dir=output_dir,
            token=token,
            rules=rules,
            protocol=args.protocol,
            max_concurrent=args.max_concurrent,
            verbose=args.verbose,
        )
    )

    summary = build_summary(results)
    logger.info(format_summary(summary))

    sys.exit(1 if summary.failed > 0 else 0)


if __name__ == "__main__":
    main()
