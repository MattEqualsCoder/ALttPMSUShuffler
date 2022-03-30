import argparse
import json
import os
import subprocess
import sys


def save_settings(args):
    settings = args.copy()
    for key in ["game", "dry-run", "dry_run", "verbose"]:
        if key in settings:
            settings.pop(key, None)
    user_resources_path = os.path.join(".", "resources", "user")
    settings_path = os.path.join(user_resources_path, "manifests")
    if not os.path.exists(settings_path):
        os.makedirs(settings_path)
    with open(os.path.join(settings_path, "settings.json"), "w+") as f:
        f.write(json.dumps(settings, indent=2))
    os.chmod(os.path.join(settings_path, "settings.json"), 0o755)


def parse_settings():
    settings = {
        "game": "snes/zelda3",
        "collection": "..",
        "collectiondrive": ""
    }
    user_resources_path = os.path.join(".", "resources", "user")
    settings_path = os.path.join(user_resources_path, "manifests")
    if os.path.exists(os.path.join(settings_path, "settings.json")):
        with(open(os.path.join(settings_path, "settings.json"))) as json_file:
            data = json.load(json_file)
            for k, v in data.items():
                settings[k] = v
    return settings


settings = parse_settings()

parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument('--loglevel', default='info', const='info', nargs='?', choices=['error', 'info', 'warning', 'debug'], help='Select level of logging for output.')
parser.add_argument(
    '--game',
    default=settings["game"],
    help='Game Track List to load.'
)
parser.add_argument(
    '--reindex',
    help='Reindex.',
    action='store_true',
    default=False
)
parser.add_argument(
    '--dry-run',
    help='Makes script print all filesystem commands that would be executed instead of actually executing them.',
    action='store_true',
    default=False
)
parser.add_argument(
    '--verbose',
    help='Verbose output.',
    action='store_true',
    default=False
)
parser.add_argument(
    '--version',
    help='Print version number and exit.',
    action='store_true',
    default=False
)
parser.add_argument(
    '--collection',
    default=settings["collection"],
    help='Point script at another directory to find root of MSU packs.'
)
parser.add_argument(
    '--collectiondrive',
    default=settings["collectiondrive"],
    help='Point script at another drive to find root of MSU packs.'
)
args, _ = parser.parse_known_args()

PYTHON_EXECUTABLE = "python"
console, game = args.game.split('/')
filext = "sfc"

collectionroot = ""
if "win32" in sys.platform:
    collectionroot += args.collectiondrive + ":\\"
else:
    collectionroot = os.path.join(".")
collectionroot = os.path.join(collectionroot, args.collection)

save_settings(vars(args))

switches = []

if ("dry-run" in list(vars(args).keys()) and args.dry-run) or \
        ("dry_run" in list(vars(args).keys()) and args.dry_run):
    switches.append("--dry-run")
if "reindex" in list(vars(args).keys()) and args.reindex:
    switches.append("--reindex")
if "verbose" in list(vars(args).keys()) and args.verbose:
    switches.append("--verbose")
if "version" in list(vars(args).keys()) and args.version:
    args.loglevel = "debug"
    switches.append("--version")

for kv in [
  ["--loglevel",    args.loglevel],
  ["--game",        f"{console}/{game}"],
  ["--gamefile",    f"{game}-msu.{filext}"],
  ["--outputpath",  f"{os.path.join('.', 'resources', 'user', console, game + '-msu')}"],
  ["--collection",  f"{os.path.join(collectionroot, console, game)}"],
  ["--copy"],
]:
    switches.append("=".join(kv))

subprocess.run(
    [
        PYTHON_EXECUTABLE,
        os.path.join("Main.py"),
        *switches
    ]
)
