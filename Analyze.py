import argparse
import colorlog
import glob
import json
import logging
import os
import re
import sys

def string_to_pairs(s, pairs=re.compile(r"(\D*)(\d*)").findall):
    return [(text.lower(), int(digits or 0)) for (text, digits) in pairs(s)[:-1]]

global LOGGER
LOGGER = None

parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
# CRITICAL: 50
# ERROR:    40
# WARNING:  30 <-- disable default logging
# INFO:     20 <-- default
# DEBUG:    10
# NOTSET:    0
parser.add_argument(
    '--loglevel',
    default='info',
    const='info',
    nargs='?',
    choices=['error', 'info', 'warning', 'debug'],
    help='Select level of logging for output.'
)
parser.add_argument(
    '--pack',
    default=os.path.join("."),
    help='Point to root of pack to analyze'
)
parser.add_argument(
    '--author',
    default='<AUTHOR>',
    help='Pack Author'
)
parser.add_argument(
    '--packname',
    default='<NAME>',
    help='Pack Name'
)
parser.add_argument(
    '--packdesc',
    default='<DESC>',
    help='Pack Description'
)
parser.add_argument(
    '--credit',
    default='<ORIGINAL_CREDIT>',
    help='Original Credit'
)
parser.add_argument(
    '--url',
    default='<URL>',
    help='README URL'
)
parser.add_argument(
    '--game',
     default="snes/zelda3",
     help='Game Track List to load.'
)

args, _ = parser.parse_known_args()

# set up logger
loglevel = {'error': logging.ERROR, 'info': logging.INFO,'warning': logging.WARNING, 'debug': logging.DEBUG}[args.loglevel]
logging.root.setLevel(loglevel)
formatter = colorlog.ColoredFormatter(
    "%(log_color)s%(levelname)s%(reset)s: %(message_log_color)s%(message)s",
    log_colors={
        "DEBUG": "thin_cyan",
        "INFO": "thin_green",
        "WARNING": "thin_yellow",
        "ERROR": "thin_red",
        "CRITICAL": "bold_red"
    },
    secondary_log_colors={
        "message": {
            "WARNING": "yellow",
            "ERROR": "red",
            "CRITICAL": "bold_red"
        }
    }
)
stream = logging.StreamHandler()
stream.setLevel(loglevel)
stream.setFormatter(formatter)
LOGGER = logging.getLogger("pythonConfig")
LOGGER.setLevel(loglevel)
LOGGER.addHandler(stream)

if args.pack != "":
    if not os.path.exists(args.pack):
        LOGGER.error(f"'{os.path.join(args.path)}' not found!")
        sys.exit()

    print(f"GameID:    {args.game}")
    print(f"Analyzing: {args.pack}")
    print("")

    analysis = {
      "author": args.author,
      "packs": [
        {
          "name": args.packname,
          "description": args.packdesc,
          "credit": {
            "name": args.credit
          },
          "url": args.url,
          "extended": [],
          "alternates": {}
        }
      ]
    }

    with(open(os.path.join(".","resources", *args.game.split("/"), "manifests", "tracks.json"))) as manifestFile:
        manifestJSON = json.load(manifestFile)
        # Extended Tracks
        if "tracks" in manifestJSON and \
            "basic" in manifestJSON["tracks"] and \
            "extended" in manifestJSON["tracks"]:
            extStart = len(manifestJSON["tracks"]["basic"]) + 1
            extEnd = extStart + len(manifestJSON["tracks"]["extended"])
            extendedTracks = []
            for tracknum, track in enumerate(manifestJSON["tracks"]["basic"]):
                if "extended" in track and track["extended"]:
                    extendedTracks.append(tracknum + 1)
            for x in list(range(extStart, extEnd)):
                extendedTracks.append(x)

            extended = []
            for filename in sorted(glob.glob(os.path.join(args.pack, "**", "*.pcm"), recursive=True), key=string_to_pairs):
                alternate = False
                if os.sep in filename.replace(args.pack, ""):
                    alternate = True
                tracknum = re.search(r'-(\d*).pcm', filename)
                if tracknum:
                    tracknum = tracknum.group(1)
                else:
                    tracknum = filename.replace(args.pack, "").split(os.sep)[0]
                if alternate:
                    if tracknum not in analysis["packs"][0]["alternates"]:
                        analysis["packs"][0]["alternates"][tracknum] = []
                    analysis["packs"][0]["alternates"][tracknum].append(filename.replace(args.pack, ""))
                if tracknum.isnumeric() and int(tracknum) in extendedTracks:
                    extended.append(int(tracknum))
            analysis["packs"][0]["extended"] = extended
    print(json.dumps(analysis, indent=2))

else:
    LOGGER.error(f"No path provided! '{os.path.join(args.path)}' given.")
    sys.exit()
