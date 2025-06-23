"""
google‑adk agent stub.

Phase 4 will wire it to an LLM toolchain; for now we only echo the transcript.
"""

from typing import List, Dict


def extract_tasks(transcript: str) -> List[str]:
    """Naive implementation – returns lines beginning with 'ACTION:'."""
    return [line.split("ACTION:", 1)[1].strip()
            for line in transcript.splitlines()
            if "ACTION:" in line]


def main() -> None:  # allows `python -m agents.task_extractor path.txt`
    import argparse, pathlib, json

    parser = argparse.ArgumentParser()
    parser.add_argument("file", type=pathlib.Path, help="Transcript text file")
    args = parser.parse_args()

    content = args.file.read_text(encoding="utf‑8")
    print(json.dumps({"tasks": extract_tasks(content)}, indent=2))


if __name__ == "__main__":
    main()
