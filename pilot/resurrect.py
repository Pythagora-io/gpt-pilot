import argparse
import os
import sys
import json

from dotenv import load_dotenv
load_dotenv()

from database.models.components.base_models import database
from database.models.development_steps import DevelopmentSteps
from database.models.file_snapshot import FileSnapshot
from database.models.files import File


def store_conversation(root_dir: str, ds: DevelopmentSteps):
    with open(os.path.join(root_dir, "CONVO.log"), "w", encoding="utf-8") as f:
        print(f"PROMPT: {ds.prompt_path}", file=f)
        for msg in ds.messages:
            print("\n" + 120 * "*", file=f)
            print(f"ROLE: {msg['role']}", file=f)
            print(120 * "-", file=f)
            print(msg['content'], file=f)
        if ds.llm_response is not None:
            print("\n" + 120 * "*", file=f)
            print(f"ROLE: assistant", file=f)
            print(120 * "-", file=f)
            print(ds.llm_response['text'], file=f)

    convo = ds.messages[:]
    if ds.llm_response is not None:
        convo.append({"role": "assistant", "content": ds.llm_response['text']})

    with open(os.path.join(root_dir, "CONVO.json"), "w", encoding="utf-8") as f:
        json.dump(convo, f, indent=2)


def output_files(root_dir: str, ds: DevelopmentSteps):
    for snapshot in ds.files:
        path = f"{snapshot.file.path}/{snapshot.file.name}"
        if path.startswith("/"):
            path = path[1:]

        full_path = os.path.join(root_dir, path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(snapshot.content)


def output_dev_step(root_dir: str, ds: DevelopmentSteps):
    print(f"Restoring DevStep {ds.id} ({ds.prompt_path}) → {root_dir}")
    store_conversation(root_dir, ds)
    output_files(root_dir, ds)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("app_id", help="App ID")
    parser.add_argument("output_dir", help="Output directory")
    parser.add_argument("--step", help="Development Step (if not specified, all)")
    args = parser.parse_args()

    if not os.path.exists(args.output_dir):
        sys.stderr.write(f"Output directory {args.output_dir} does not exist\n")
        sys.exit(-1)

    database.connect()

    if args.step is not None:
        output_dev_step(args.output_dir, DevelopmentSteps.get(app=args.app_id, id=args.step))
        return

    for ds in DevelopmentSteps.select().where(DevelopmentSteps.app == args.app_id):
        step_dir = os.path.join(args.output_dir, str(ds.id))
        os.makedirs(step_dir, exist_ok=True)
        output_dev_step(step_dir, ds)


if __name__ == "__main__":
    main()
