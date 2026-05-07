import argparse
import json
import sys
import types
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def _ensure_package_import():
    """Allow this script to be run directly from the repository root."""
    if "DrafterBench" not in sys.modules:
        package = types.ModuleType("DrafterBench")
        package.__path__ = [str(ROOT)]
        sys.modules["DrafterBench"] = package


def parse_args():
    parser = argparse.ArgumentParser(
        description="Generate scalable DrafterBench extension tasks."
    )
    parser.add_argument(
        "--mode",
        choices=["scale", "expand"],
        required=True,
        help="Use 'scale' for single-turn scalable task generation or 'expand' for multi-turn task generation.",
    )
    parser.add_argument(
        "--num",
        type=int,
        default=1,
        help="Number of generated tasks per task family.",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output JSON file. Defaults to scaled_tasks.json or expanded_tasks.json.",
    )
    parser.add_argument("--model", type=str, default=None, help="Generation model name.")
    parser.add_argument(
        "--model-provider",
        type=str,
        default=None,
        help="LiteLLM provider name for the generation model.",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=None,
        help="Generation temperature.",
    )
    parser.add_argument(
        "--max-completion-tokens",
        type=int,
        default=None,
        help="Maximum completion tokens for instruction generation.",
    )
    return parser.parse_args()


def main():
    _ensure_package_import()
    args = parse_args()

    if args.mode == "scale":
        from DrafterBench.scal_extension.scalingup_pipline import scalup

        tasks = scalup(
            args.num,
            model=args.model,
            provider=args.model_provider,
            temperature=args.temperature,
            max_completion_tokens=args.max_completion_tokens,
        )
        output_path = args.output or "scaled_tasks.json"
    else:
        from DrafterBench.scal_extension.expension_pipline import new_multiturn_task

        tasks = new_multiturn_task(
            args.num,
            model=args.model,
            provider=args.model_provider,
            temperature=args.temperature,
            max_completion_tokens=args.max_completion_tokens,
        )
        output_path = args.output or "expanded_tasks.json"

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(tasks, f, indent=2, ensure_ascii=False)

    print(f"Saved {len(tasks)} tasks to {output_path}.")


if __name__ == "__main__":
    main()
