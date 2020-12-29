import argparse
import json
import os
import subprocess
import sys

def save_settings(args):
  settings = args.copy()
  for key in ["game","dry-run", "dry_run"]:
    if key in settings:
      settings.pop(key, None)
  user_resources_path = os.path.join(".","resources","user")
  settings_path = os.path.join(user_resources_path,"manifests")
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
  user_resources_path = os.path.join(".","resources","user")
  settings_path = os.path.join(user_resources_path,"manifests")
  if os.path.exists(os.path.join(settings_path,"settings.json")):
      with(open(os.path.join(settings_path,"settings.json"))) as json_file:
          data = json.load(json_file)
          for k, v in data.items():
              settings[k] = v
  return settings

settings = parse_settings()

parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument('--game', default=settings["game"], help='Game Track List to load.')
parser.add_argument('--dry-run', help='Makes script print all filesystem commands that would be executed instead of actually executing them.', action='store_true', default=False)
parser.add_argument('--collection', default=settings["collection"], help='Point script at another directory to find root of MSU packs.')
parser.add_argument('--collectiondrive', default=settings["collectiondrive"], help='Point script at another drive to find root of MSU packs.')
args, _ = parser.parse_known_args()

PYTHON_EXECUTABLE = "python"
console,game = args.game.split('/')
filext = "sfc"

collectionroot = ""
if "win32" in sys.platform:
  collectionroot += args.collectiondrive + ":\\"
else:
  collectionroot = os.path.join(".")
collectionroot = os.path.join(collectionroot,args.collection)

save_settings(vars(args))

switches = [
  "--game", console + '/' + game,
  "--gamefile", game + "-msu" + '.' + filext,
  "--outputpath", os.path.join(".", "resources", "user", console,game + "-msu", ""),
  "--collection", os.path.join(collectionroot,console,game),
  "--copy"
]

if "dry-run" in list(vars(args).keys()) or "dry_run" in list(vars(args).keys()):
  switches.append("--dry-run")

subprocess.check_call([
  PYTHON_EXECUTABLE,
  os.path.join("Main.py"),
  *switches
])
