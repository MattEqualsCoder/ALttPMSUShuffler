import colorlog
import websockets

from pathlib import Path
from tempfile import TemporaryDirectory

import argparse
import asyncio
import datetime
import glob
import json
import logging
import os
import pickle
import pprint
import random
import re
import sched
import shutil
import sys
import time

__version__ = '0.8.2'

# Creates a shuffled MSU-1 pack for ALttP Randomizer from one or more source
# MSU-1 packs.
#
# Usage:
#
# 1) Copy this script to a new subdirectory in the directory containing all
#    of your current MSU packs.  For example, if your MSU pack is in
#    `"MSUs\alttp_undertale\alttp_msu-1.pcm"`, the script should be in
#    `"MSUs\ALttPMSUShuffler\Main.py"`.
#
# 2) DRAG AND DROP METHOD:
#
#     1) Drag one or more ALttP Randomizer ROMs (with background music enabled)
#        on top of Main.py to open the ROMs with the python script; for each ROM
#        opened this way, a shuffled MSU pack matching that ROM's name will be
#        generated next to the ROM in its original directory (with the tracklist
#        in ROMNAME-msushuffleroutput.log).
#
# 3) MANUAL METHOD:
#
#     1) Copy the ALttP Randomizer ROM (with background music enabled) to the
#        same directory as this Main.py script.  The script will rename the ROM
#        to "shuffled.sfc".  The original ROM name and tracklist is printed to
#        "shuffled-msushuffleroutput.log" (handy for retrieving spoilers).  If
#        you don't copy the ROM before running the script, you need to rename
#        the ROM to "shuffled.sfc" yourself.  The script will warn before
#        overwriting "shuffled.sfc" if it already exists.
#
#     2) Run **Main.py** to execute the script to delete any old pack in this
#        directory and generate a new one.  Track names picked will be saved in
#        "shuffled-msushuffleroutput.log" (cleared on reruns)
#
#     3) LIVE RESHUFFLE METHOD: Instead of simply running
#        **Main.py**, run **LiveReshuffle.py** or run in the command line as
#        "python Main.py --live 10" (or any other positive integer) to
#        generate a new shuffled MSU pack every few seconds.  Will skip
#        replacing any tracks currently being played.  Best if used without
#        the --realcopy option, and best if the shuffled MSU pack and source
#        packs are all on the same hard drive, to avoid excessive disk usage.
#        Edit **LiveReshuffle.py** to set a different reshuffle interval than
#        the 10 second default.
#
#     4) LIVE RESHUFFLE + NOW PLAYING VIEW (EXPERIMENTAL): Run the command
#        line as "python Main.py --live 10 --nowplaying" to run in live
#        reshuffle mode (as described above) while polling qusb2snes for
#        the currently playing MSU pack, printed to console and nowplaying.txt
#        for use as an OBS streaming text source.
#
# 4) Load the ROM in an MSU-compatible emulator (works well with Snes9x 1.60)
#
# Additional options/usage notes:
#
# - By default, the generated pack will pick each track from a matching
#   track number in a random MSU pack in the parent directory of this
#   script.  For dungeon-specific or boss-specific tracks, if the random
#   pack chosen isn't an extended MSU pack, the generic dungeon/boss music
#   is chosen instead.
#
#   Note that if you ONLY have non-extended packs, this
#   default behavior will create an extended pack, which (like all extended
#   packs) prevents you from using music cues to distinguish pendant from
#   crystal dungeons.  If you want this, use --basicshuffle instead.
#
# - If run in the command line as "python Main.py --basicshuffle", each
#   track is chosen from the same track from a random pack.  If you have any
#   extended packs, the dungeon/boss themes from non-extended packs will
#   never be chosen.
#
# - If run in the command line as "python Main.py --fullshuffle", behavior
#   for non-looping tracks (short fanfares, portals, etc.) remains as
#   default, but looping tracks will be in shuffled order, so each track
#   in the generated pack is chosen from a random track number in a random
#   MSU pack.  Pick this if you like shop music in Ganon's Tower.
#
# - If run in the command line as
#   "python Main.py --singleshuffle ../your-msu-pack-name-here", behavior is
#   the same as with --fullshuffle, but a single MSU pack of your choice is
#   chosen as the shuffled source for all tracks in the generated pack.
#
# - If run in the command line as "python Main.py --higan" (along with any
#   other options), the shuffled MSU pack is generated in a higan-friendly
#   subdirectory "./higan.sfc/"
#
# - Searches the parent directory of the directory containing the script for
#   all MSU packs to be included in the shuffler by default, but will skip
#   any tracks with "disabled" (case-insensitive) in the directory name or
#   file name; useful for keeping tracks hidden from the shuffler without
#   needing to move them out of the collection entirely.
#
# - Caches the track list in ./trackindex.pkl to avoid reindexing the entire
#   collection every time the script is run.  If run in the command line as
#   "python Main.py --reindex", it will regenerate the track index.  Use this
#   to pick up any new MSU packs for the shuffler.
#
#  Debugging options (not necessary for normal use):
#
# - This script uses hardlinks instead of copies by default to reduce disk
#   usage and increase speed; the --realcopy option can be used to create
#   real copies instead of hardlinks.  Real copies are forced if the shuffled
#   MSU pack and the source MSU packs are on different hard drives.
#
# - The --dry-run option can be used to make this script print the filesystem
#   commands (deleting, creating, renaming files) it would have executed
#   instead of executing them.

LJUST = 35

meta = {} # hash
titles = {} # hash
higandir = ""
trackdatapath = {} # string
longestTrackName = {} # int
nonloopingtracks = {} # array
extendedmsutracks = {} # array
extendedbackupdict = {} # hash

# get track list
# get track titles
# sort non/looping tracks
# get extended tracks
# get extended backup tracks
def load_game(gamepath, gameID):
    global LOGGER
    global titles
    global trackdatapath
    global longestTrackName
    global nonloopingtracks
    global extendedmsutracks
    global extendedbackupdict

    console,game = gamepath.split('/')

    trackdatapath[gamepath] = os.path.join(".", "resources", console, game, "manifests", "tracks.json")
    trackdata = {}
    trackdata[gamepath] = {}
    if gamepath not in titles:
      titles[gamepath] = {}
    if gamepath not in nonloopingtracks:
      nonloopingtracks[gamepath] = []
    if gamepath not in extendedmsutracks:
      extendedmsutracks[gamepath] = []
    if os.path.exists(trackdatapath[gamepath]):
      with open(trackdatapath[gamepath]) as json_file:
        trackdata[gamepath] = json.load(json_file)
        meta[gamepath] = trackdata[gamepath]["meta"] if "meta" in trackdata[gamepath] else {}

    if "tracks" in trackdata[gamepath]:
      i = trackdata[gamepath]["tracks"]["index"] if "index" in trackdata[gamepath]["tracks"] else 1
      if "basic" in trackdata[gamepath]["tracks"]:
        for track in trackdata[gamepath]["tracks"]["basic"]:
          title = ""
          if "unused" in track or "title" not in track:
              title = "<Unused>"
          elif "title" in track:
              title = track["title"]
          if "num" in track:
              i = track["num"]
          titles[gamepath][str(i)] = title
          #Tracks that don't loop; this is used to prevent a non-looping track from
          #being shuffled with a looping track (nobody wants the boss fanfare as
          #light world overworld music)
          if "nonlooping" in track:
            if track["nonlooping"]:
              nonloopingtracks[gamepath].append(str(i))
          i += 1
      if "extended" in trackdata[gamepath]["tracks"]:
        for track in trackdata[gamepath]["tracks"]["extended"]:
          title = ""
          if "unused" in track or "title" not in track:
              title = "<Unused>"
          elif "title" in track:
              title = track["title"]
          if "num" in track:
              i = track["num"]
          titles[gamepath][str(i)] = title
          #List of extended MSU dungeon-specific and boss-specific tracks.
          extendedmsutracks[gamepath].append(str(i))

          #Since the presence of any dungeon/boss-specific track from an extended MSU
          #pack overrides the generic pendant/crystal dungeon or generic boss music,
          #a basic shuffle always picking track N as that same track N from a random
          #pack will result in no boss/dungeon music from a non-extended pack ever
          #being chosen if the user has a single extended pack.
          #
          #To allow dungeon/boss music to be played, the dungeon/boss-specific
          #extended MSU tracks are shuffled differently; for each extended
          #dungeon/boss-specific track, a pack is chosen randomly, then its
          #corresponding dungeon/boss-specific track is chosen if present,
          #otherwise, the generic dungeon/boss music from that pack is chosen.
          #
          #This means that a user that ONLY has non-extended packs won't be able to
          #listen to dungeon music to determine crystal/pendant status in modes where
          #that applies (since EP/DP/TH would always play light world music from a
          #random pack regardless of pendant/crystal status).  To preserve that
          #behavior, --basicshuffle can be used.
          if gamepath not in extendedbackupdict:
            extendedbackupdict[gamepath] = {}
          if "fallback" in track:
            extendedbackupdict[gamepath][i] = track["fallback"]

          i += 1
      if "longest" in trackdata[gamepath]["tracks"]:
          if gamepath not in longestTrackName:
            longestTrackName[gamepath] = ""
          longestTrackName[gamepath] = trackdata[gamepath]["tracks"]["longest"]

    LOGGER.debug(f"Loading Game: {console}/{game}")
    for k in ["basic","extended"]:
        if k in trackdata[gamepath]:
            LOGGER.debug(f"{k.capitalize()} Tracks: {len(trackdata[gamepath]['tracks'][k])}")

    # Globals used by the scheduled reshuffle in live mode (couldn't figure out
    # a better way to pass dicts/lists to shuffle_all_tracks when called by
    # the scheduler)
    global trackindex
    trackindex = {}
    trackindex[gamepath] = {}
    global nonloopingfoundtracks
    nonloopingfoundtracks = {}
    nonloopingfoundtracks[gamepath] = []
    global loopingfoundtracks
    loopingfoundtracks = {}
    loopingfoundtracks[gamepath] = []
    global shuffledloopingfoundtracks
    shuffledloopingfoundtracks = {}
    shuffledloopingfoundtracks[gamepath] = {}
    s = sched.scheduler(time.time, time.sleep)

# delete old log
# delete old higan dir
# copy new game file
# delete old pcms
def delete_old_msu(args, rompath):
    global LOGGER

    LOGGER.debug("Deleting old MSU")

    try:
        if os.path.exists(f"{rompath}-msushuffleroutput.log"):
            os.remove(f"{rompath}-msushuffleroutput.log")
    except PermissionError:
        LOGGER.warning(f"Failed to clear old logfile: '{rompath}-msushuffleroutput.log'")

    output_file_handler = logging.FileHandler(f"{rompath}-msushuffleroutput.log")
    LOGGER.addHandler(output_file_handler)

    if (args.dry_run):
        LOGGER.info("DRY RUN MODE: Printing instead of executing.")
        LOGGER.info("")

    foundsrcrom = False
    foundshuffled = False
    gamefiles = []
    romname = args.gamefile if args.gamefile != "" else ""

    if romname != "":
        gamefiles.append(
            (
                os.path.dirname(romname),
                os.path.basename(romname)
            )
        )
    else:
        for path in glob.glob('*.sfc'):
            gamefiles.append(
                (
                    os.path.dirname(path),
                    os.path.basename(path)
                )
            )

    for path,romname in gamefiles:
        if romname != "":
            if romname != "shuffled.sfc" and "higan" not in romname:
                srcrom = romname
                foundsrcrom = True
            else:
                srcrom = romname
                foundshuffled = True

    if args.higan:
        if os.path.isdir(higandir):
            if args.dry_run:
                LOGGER.info(f"DRY RUN MODE: Would rmtree: '{higandir}'")
            else:
                shutil.rmtree(higandir)
        if args.dry_run:
            LOGGER.info(f"DRY RUN MODE: Would make: '{os.path.join(higandir,'msu.rom')}'")
        else:
            os.mkdir(higandir)
            open(os.path.join(higandir, "msu1.rom"), 'a').close()

    if foundsrcrom or foundshuffled:
        if args.higan:
            if args.dry_run:
                LOGGER.info(
                    "DRY RUN MODE: Would copy: '%s' to '%s'"
                    %
                    os.path.basename(srcrom),
                    os.path.join(higandir, "program.rom")
                )
            else:
                LOGGER.info(f"Copying: {os.path.basename(srcrom)} to {os.path.join(higandir, 'program.rom')}")
                shutil.copy(srcrom, os.path.join(higandir, "program.rom"))
                shutil.copy(srcrom, os.path.join(higandir, "program.sfc"))
        else:
            replace = "Y"
            if foundshuffled:
                replace = "Y"
            if replace.upper() == "Y":
                if (args.dry_run):
                    LOGGER.info(
                        "DRY RUN MODE: Would %s '%s' to '%s.sfc'"
                        %
                        (
                          ('copy' if args.copy else 'rename'),
                          os.path.basename(srcrom),
                          rompath
                        )
                    )
                else:
                    if args.copy:
                        LOGGER.info(f"Copying '{os.path.basename(srcrom)}' to '{rompath}.sfc'")
                        shutil.copy(srcrom, f"{rompath}.sfc")
                    else:
                        LOGGER.info(f"Renaming '{os.path.basename(srcrom)}' to '{rompath}.sfc'")
                        shutil.move(srcrom, f"{rompath}.sfc")
    else:
        make_romless = str(input(f"INPUT: No gamefile found at: '{rompath}.sfc' . Continue making pack? [y/n]") or "Y")
        if make_romless.upper() != "Y":
            LOGGER.error("User selected to exit without making pack without gamefile.")
            sys.exit(1)

    if not args.higan:
        for path in glob.glob(f'{rompath}-*.pcm'):
            if (args.dry_run):
                LOGGER.info(f"DRY RUN MODE: Would remove: '{str(path)}'")
            else:
                try:
                    os.remove(str(path))
                except PermissionError:
                    LOGGER.warning(f"Failed to remove: '{path}'")

# copy track
def copy_track(srcpath, dst, rompath, dry_run, higan, forcerealcopy, live, tmpdir, gamepath, gameID):
    global LOGGER

    if higan:
        dstpath = os.path.join(higandir, f"track-{str(dst)}.pcm")
        if "z3m3" in gameID:
            dstpath = os.path.join(higandir, f"track-{str(dst + 100)}.pcm")
    else:
        dstpath = f"{rompath}-{dst}.pcm"
        if "z3m3" in gameID and "zelda3" in gamepath:
            dstpath = (
                "%s-%s.pcm"
                %
                (
                    rompath,
                    int(dst) + 100
                )
            )

    for match in re.finditer(r'\d+', os.path.basename(srcpath)):
        pass
    srctrack = int(match.group(0))

    if str(srctrack) not in list(titles[gamepath].keys()):
        return

    srctitle = titles[gamepath][str(srctrack)]

    if "<Unused>" in srctitle:
        return

    shorttitle = ('(' + srctitle[srctitle.find('-')+2:] + ") ") if int(srctrack) != int(dst) else ""
    dsttitle = titles[gamepath][str(dst)]

    if not live:
        shortsrcpath = srcpath
        if args.collection:
            shortsrcpath = shortsrcpath.replace(args.collection,"")
        if shortsrcpath[:1] == '\\':
            shortsrcpath = shortsrcpath[1:]
        msg = str(srctrack).rjust(3, '0') + " - " + (dsttitle + ': ' + shorttitle).ljust(longestTrackName[gamepath] + 8, ' ') + shortsrcpath
        if args.verbose:
            msg += " -> " + dstpath
        LOGGER.info(msg)

    if not dry_run:
        try:
            # Use a temporary file and os.replace to get around the fact that
            # python doesn't have an atomic copy/hardlink with overwrite.
            tmpname = os.path.join(tmpdir, f"tmp{os.path.basename(dstpath)}")

            if (forcerealcopy):
                shutil.copy(srcpath, tmpname)
            else:
                os.link(srcpath, tmpname)

            os.replace(tmpname, dstpath)
            return True
        except PermissionError:
            if not live:
                LOGGER.info(f"Failed to copy '{srcpath}' to '{dstpath}' during non-live update")
            return False

# Build a dictionary mapping each possible track number to all matching tracks
# in the search directory; do this once, to avoid excess searching later.
#
# In default mode (non-basic/non-full), since we want non-extended MSU packs to
# still have their dungeon/boss music represented in the shuffled pack, match
# the generic backups for each of the extended MSU tracks.
#
# Index format:
# index[2] = ['../msu1/track-2.pcm', '../msu2/track-2.pcm']
def build_index(args, game):
    global LOGGER
    global trackindex


    if os.path.exists('trackindex.pkl') and not args.reindex:
        with open('trackindex.pkl', 'rb') as f:
            try:
                trackindex = pickle.load(f)
            except Exception as e:
                LOGGER.error("Failed to load track index")

        if trackindex:
            LOGGER.info("Reusing track index, run with --reindex to pick up any new packs.")
            return

    LOGGER.info("Index: Building. This should take a few seconds.")
    buildstarttime = datetime.datetime.now()

    if (args.singleshuffle):
        searchdir = args.singleshuffle
    elif "z3m3" in args.game:
        searchdir = args.collection.replace("snes\z3m3", game)
    elif args.collection:
        searchdir = args.collection
    else:
        searchdir = os.path.join("..")

    gamepath = game
    if "name" in meta[gamepath]:
        LOGGER.info("")
        LOGGER.info(f"Processing MSU for {meta[gamepath]['name']}")
    LOGGER.info("")
    LOGGER.info("Using gamepath at:".ljust(LJUST) + gamepath)
    LOGGER.info("Using manifest at:".ljust(LJUST) + trackdatapath[gamepath])
    LOGGER.info("Using gamefile at:".ljust(LJUST) + (args.gamefile if args.gamefile else "*.sfc"))
    LOGGER.info("Using collection at:".ljust(LJUST) + os.path.join(searchdir,"*"))

    if args.higan:
        args.outputprefix = "track"
        LOGGER.info("Outputting to:".ljust(LJUST) + os.path.join(higandir,args.outputprefix) + '*')
    else:
        LOGGER.info("Outputting to:".ljust(LJUST) + os.path.join(args.outputpath,args.outputprefix) + '*')

    #For all packs in the target directory, make a list of found track numbers.
    allpacks = list()
    for path in Path(searchdir).rglob('*.pcm'):
        pack = os.path.dirname(str(path))
        if 'disabled' not in pack.lower():
            name = os.path.basename(str(path))[:8]
            if pack not in allpacks and name != "shuffled":
                allpacks.append(pack)

    if not allpacks:
        LOGGER.error("Couldn't find any MSU packs in:".ljust(LJUST) + os.path.abspath(str(searchdir)))
        return

    for pack in allpacks:
        for track in list(range(0, int(list(titles[gamepath].keys())[-1]) + 1)):
            foundtracks = list()
            for path in Path(pack).rglob(f"*-{track}.pcm"):
                trackname = os.path.basename(str(path))
                if 'disabled' not in trackname.lower():
                    foundtracks.append(str(path))

            #For extended MSU packs, use the backups
            if not args.basicshuffle and not args.fullshuffle:
                if not foundtracks and track in extendedmsutracks[gamepath] and track in extendedbackupdict[gamepath]:
                    backuptrack = extendedbackupdict[gamepath][track]
                    for path in Path(pack).rglob(f"*-{backuptrack}.pcm"):
                        trackname = os.path.basename(str(path))
                        if 'disabled' not in trackname.lower():
                            foundtracks.append(str(path))

            trackindex[gamepath].setdefault(track, []).extend(foundtracks)

    #Uncomment to print index for debugging
    #pp = pprint.PrettyPrinter()
    #pp.pprint(trackindex)

    buildtime = datetime.datetime.now() - buildstarttime
    LOGGER.info(f"Index: Build took {buildtime.seconds}.{buildtime.microseconds} seconds.")
    LOGGER.info("")

# do the shuffle and write pcms
def shuffle_all_tracks(rompath, fullshuffle, singleshuffle, dry_run, higan, forcerealcopy, live, nowplaying, cooldown, prevtrack, gamepath, gameID):
    global LOGGER

    with open('trackindex.pkl', 'wb') as f:
        # Saving track index as plaintext instead of HIGHEST_PROTOCOL since
        # this is only loaded once, and plaintext may be useful for debugging.
        pickle.dump(trackindex, f, 0)

    #For all found non-looping tracks, pick a random track with a matching
    #track number from a random pack in the target directory.
    shufflestarttime = datetime.datetime.now()

    if not live:
        LOGGER.info("")
        LOGGER.info("Non-looping tracks:")

    if cooldown == 0:
        with TemporaryDirectory(dir='.') as tmpdir:
            oldwinnerdict = {}
            if os.path.exists('winnerdict.pkl'):
                with open('winnerdict.pkl', 'rb') as f:
                    try:
                        oldwinnerdict = pickle.load(f)
                    except Exception as e:
                        LOGGER.error("Failed to load tracklist")
            winnerdict = {}
            for i in nonloopingfoundtracks[gamepath]:
                winner = random.choice(list(trackindex[gamepath].values())[int(i)])
                winnerdict[i] = winner
                copy_track(
                    winner,
                    i,
                    rompath,
                    dry_run,
                    higan,
                    forcerealcopy,
                    live,
                    tmpdir,
                    gamepath,
                    gameID
                )

            #For all found looping tracks, pick a random track from a random pack
            #in the target directory, with a matching track number by default, or
            #a shuffled different looping track number if fullshuffle or
            #singleshuffle are enabled.
            if not live:
                LOGGER.info("")
                LOGGER.info("Looping tracks:")
            for i in loopingfoundtracks[gamepath]:
                if (args.fullshuffle or args.singleshuffle):
                    dst = i
                    src = shuffledloopingfoundtracks[loopingfoundtracks[gamepath].index(i)]
                else:
                    dst = i
                    src = i
                winner = random.choice(list(trackindex[gamepath].values())[int(src)])
                copied = copy_track(
                    winner,
                    dst,
                    rompath,
                    dry_run,
                    higan,
                    forcerealcopy,
                    live,
                    tmpdir,
                    gamepath,
                    gameID
                )
                # if copy failed, use OLD winner...
                if copied:
                    winnerdict[i] = winner
                elif i in oldwinnerdict:
                    winnerdict[i] = oldwinnerdict[i]

            with open('winnerdict.pkl', 'wb') as f:
                pickle.dump(winnerdict, f, pickle.HIGHEST_PROTOCOL)
        if live:
            cooldown = int(live)
            if not nowplaying:
                shuffletime = datetime.datetime.now() - shufflestarttime

            LOGGER.info(
                "Reshuffling MSU pack every%s second%s, press CTRL+C or close the window to stop reshuffling. (Shuffled in %d.%ds)"
                %
                (
                    " " + str(int(live)) if int(live) != 1 else "",
                    "s" if int(live) != 1 else "",
                    shuffletime.seconds,
                    shuffletime.microseconds
                )
            )

    if live:
        if nowplaying:
            newtrack = read_track(prevtrack)
            prevtrack = newtrack
        s.enter(
            1,
            1,
            shuffle_all_tracks,
            argument=(
                rompath,
                fullshuffle,
                singleshuffle,
                dry_run,
                higan,
                forcerealcopy,
                live,
                nowplaying,
                cooldown - 1,
                prevtrack,
                gamepath,
                gameID
            )
        )

async def recv_loop(ws, recv_queue):
    try:
        async for msg in ws:
            recv_queue.put_nowait(msg)
    finally:
        await ws.close()

# Print the track that's currently playing, and print its pack to
# nowplaying.txt which can be used as a streaming text file source.
def print_pack(path):
    global LOGGER

    LOGGER.info(f"Now playing: {path}")
    path_parts = list()
    while True:
        parts = os.path.split(path)
        if parts[0] == path:
            path_parts.insert(0, parts[0])
            break
        elif parts[1] == path:
            path_parts.insert(0, parts[1])
            break
        else:
            path = parts[0]
            path_parts.insert(0, parts[1])
    with open('nowplaying.txt', 'w') as f:
        f.truncate(0)
        LOGGER.info("MSU pack now playing:", file=f)
        LOGGER.info(path_parts[1], file=f)

async def query(prevtrack):
    global LOGGER
    addr = "ws://localhost:8080"
    try:
        ws = await websockets.connect(addr, ping_timeout=None, ping_interval=None)
    except Exception as e:
        LOGGER.error("Failed to connect to qusb2snes")
        return 0

    devlist = {
        "Opcode": "DeviceList",
        "Space": "SNES"
    }
    await ws.send(json.dumps(devlist))
    reply = json.loads(await ws.recv())
    devices = reply['Results'] if 'Results' in reply and len(reply['Results']) > 0 else None
    if not devices:
        LOGGER.error("Failed to connect to SNES through qusb2snes")
        await ws.close()
        return 0

    device = devices[0]
    attachreq = {
        "Opcode": "Attach",
        "Space": "SNES",
        "Operands": [device]
    }
    await ws.send(json.dumps(attachreq))

    recv_queue = asyncio.Queue()
    recv_task = asyncio.create_task(recv_loop(ws, recv_queue))
    WRAM_START = 0xF50000

    # Current MSU is $010B, per https://github.com/KatDevsGames/z3randomizer/blob/master/msu.asm#L126
    REG_CURRENT_MSU_TRACK = 0x010B

    address = WRAM_START + REG_CURRENT_MSU_TRACK
    size = 1
    readreq = {
        "Opcode": "GetAddress",
        "Space": "SNES",
        "Operands": [hex(address)[2:], hex(size)[2:]]
    }
    await ws.send(json.dumps(readreq))
    data = bytes()
    while len(data) < 1:
        try:
            data += await asyncio.wait_for(recv_queue.get(), 1)
        except asyncio.TimeoutError:
            break

    track = 0
    if len(data) != 1:
        LOGGER.warning("Failed to query REG_CURRENT_MSU_TRACK")
    else:
        track = int(data[0])

    if track != 0 and track != prevtrack:
        if os.path.exists('winnerdict.pkl'):
            winnerdict = {}
            with open('winnerdict.pkl', 'rb') as f:
                try:
                    winnerdict = pickle.load(f)
                    print_pack(str(winnerdict[track]))
                except Exception as e:
                    LOGGER.error("Failed to load tracklist")

    await ws.close()
    return track

# Read the currently playing track over qusb2snes.
# TODO: This currently opens up a new qusb2snes connection every second.
# Eventually this should be smarter by keeping one connection alive instead.
def read_track(prevtrack):
    track = asyncio.get_event_loop().run_until_complete(query(prevtrack))
    return track

def generate_shuffled_msu(args, rompath, gamepath, gameID):
    global LOGGER

    if (not os.path.exists(f'{rompath}.msu')):
        LOGGER.info(f"Dummy MSU '{rompath}.msu' doesn't exist, creating it.")
        if (not args.dry_run):
            with open(f'{rompath}.msu', 'w'):
                pass

    global nonloopingfoundtracks
    global loopingfoundtracks
    global shuffledloopingfoundtracks

    foundtracks = {}
    foundtracks[gamepath] = list()
    for key in trackindex[gamepath]:
        if trackindex[gamepath][key]:
            foundtracks[gamepath].append(key)
    foundtracks[gamepath] = sorted(foundtracks[gamepath])

    #Separate this list into looping tracks and non-looping tracks, and make a
    #shuffled list of the found looping tracks.
    for i in list(titles[gamepath].keys()):
        if int(i) in foundtracks[gamepath]:
            if str(i) in nonloopingtracks[gamepath]:
                nonloopingfoundtracks[gamepath].append(i)
            else:
                loopingfoundtracks[gamepath].append(i)

    shuffledloopingfoundtracks[gamepath] = loopingfoundtracks[gamepath].copy()
    random.shuffle(shuffledloopingfoundtracks[gamepath])

    if args.higan:
        readmepath = os.path.join(higandir,"readme")
        if not os.path.exists(readmepath):
            os.makedirs(readmepath)
        shutil.copy(os.path.join(".","resources","meta","manifests","higan","higan-msu.txt"), readmepath)

    if args.live:
        s.enter(
            1,
            1,
            shuffle_all_tracks,
            argument=(
                rompath,
                args.fullshuffle,
                args.singleshuffle,
                args.dry_run,
                args.higan,
                args.forcerealcopy,
                args.live,
                args.nowplaying,
                int(args.live),
                0,
                gamepath,
                gameID
            )
        )
        s.run()
    else:
        shuffle_all_tracks(
            rompath,
            args.fullshuffle,
            args.singleshuffle,
            args.dry_run,
            args.higan,
            args.forcerealcopy,
            args.live,
            args.nowplaying,
            0,
            0,
            gamepath,
            gameID
        )
        LOGGER.info("")
        LOGGER.info('Done.')

def main(args):
    global LOGGER

    LOGGER.debug(f"ALttPMSUShuffler version {__version__}")
    if args.version:
        exit(1)

    gamepaths = [ args.game ]
    gameID = args.game
    if gameID == "snes/z3m3":
        gamepaths = [ "snes/metroid3", "snes/zelda3" ]

    for gamepath in gamepaths:
        load_game(gamepath, gameID)
        build_index(args, gamepath)
        for rom in args.roms:
            args.forcerealcopy = args.realcopy
            try:
                # determine if the supplied rom is ON the same drive as the script. If not, realcopy is mandatory.
                os.path.commonpath([os.path.abspath(rom), os.path.abspath(__file__)])
            except:
                print(f"Failed to find common path between {os.path.abspath(rom)} and {os.path.abspath(__file__)}, forcing real copies.")
                args.forcerealcopy = True

            if args.live and args.forcerealcopy:
                LOGGER.warning("Live updates with real copies will cause a LOT of disk usage.")

            if gamepath == gamepaths[0]:
                delete_old_msu(args, rom)
            generate_shuffled_msu(args, rom, gamepath, gameID)

if __name__ == '__main__':
    global LOGGER
    LOGGER = None

    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    # CRITICAL: 50
    # ERROR:    40
    # WARNING:  30 <-- disable default logging
    # INFO:     20 <-- default
    # DEBUG:    10
    # NOTSET:    0
    parser.add_argument('--loglevel', default='info', const='info', nargs='?', choices=['error', 'info', 'warning', 'debug'], help='Select level of logging for output.')
    parser.add_argument('--collection', default=os.path.join(".."), help='Point script at another directory to find root of MSU packs.')
    parser.add_argument('--game', default="snes/zelda3", help='Game Track List to load.')
    parser.add_argument('--gamefile', default="", help='Game File to load. Leave blank to auto-locate.')
    parser.add_argument('--outputpath', default=os.path.join("."), help='Output path.')
    parser.add_argument('--outputprefix', default='shuffled', help='Output prefix.')
    parser.add_argument('--copy', action='store_true', default=False)
    parser.add_argument('--fullshuffle', help="Choose each looping track randomly from all looping tracks from all packs, rather than the default behavior of only mixing track numbers for dungeon/boss-specific tracks.  Good if you like shop music in Ganon's Tower.", action='store_true', default=False)
    parser.add_argument('--basicshuffle', help='Choose each track with the same track from a random pack.  If you have any extended packs, the dungeon/boss themes from non-extended packs will never be chosen in this mode.  If you only have non-extended packs, this preserves the ability to tell crystal/pendant dungeons by music.', action='store_true', default=False)
    parser.add_argument('--singleshuffle', help='Choose each looping track randomly from all looping tracks from a single MSU pack.  Enter the path to a subfolder in the parent directory containing a single MSU pack.')
    parser.add_argument('--higan', help='Creates files in higan-friendly directory structure.', action='store_true', default=False)
    parser.add_argument('--realcopy', help='Creates real copies of the source tracks instead of hardlinks', action='store_true', default=False)
    parser.add_argument('--dry-run', help='Makes script print all filesystem commands that would be executed instead of actually executing them.', action='store_true', default=False)
    parser.add_argument('--verbose', help='Verbose output.', action='store_true', default=False)
    parser.add_argument('--live', help='The interval at which to re-shuffle the entire pack, in seconds; will skip tracks currently in use.')
    parser.add_argument('--nowplaying', help='EXPERIMENTAL: During live reshuffling, connect to qusb2snes to print the currently playing MSU pack to console and nowplaying.txt', action='store_true', default=False)
    parser.add_argument('--reindex', help='Rebuild the index of MSU packs, this must be run to pick up any new packs or moved/deleted files in existing packs!', action='store_true', default=False)
    parser.add_argument('--version', help='Print version number and exit.', action='store_true', default=False)

    romlist = list()
    args, roms = parser.parse_known_args()

    # set up logger
    loglevel = {'error': logging.ERROR, 'info': logging.INFO, 'warning': logging.WARNING, 'debug': logging.DEBUG}[args.loglevel]

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
    LOGGER = logging.getLogger('pythonConfig')
    LOGGER.setLevel(loglevel)
    LOGGER.addHandler(stream)

    # LOGGER.debug("Debug")
    # LOGGER.info("Info")
    # LOGGER.warning("Warning")
    # LOGGER.error("Error")
    # LOGGER.critical("Critical")

    for rom in roms:
        if not os.path.exists(rom):
            LOGGER.error(f"Unknown argument {rom}")
            parser.print_help()
            sys.exit()

        romlist.append(os.path.splitext(rom)[0])

    if not romlist:
        if args.outputpath and args.outputprefix:
            if args.higan:
                rompath = os.path.join(args.outputpath, f"higan-{args.outputprefix}.sfc")
                higandir = rompath
            else:
                rompath = os.path.join(args.outputpath,args.outputprefix)
            romlist.append(rompath)
            parpath = os.path.dirname(rompath)
            if not os.path.exists(parpath):
                os.makedirs(parpath)

    if args.gamefile != "":
        if not os.path.exists(args.gamefile):
            LOGGER.error(f"'{os.path.join(args.gamefile)}' not found!")
            sys.exit()
        elif not romlist:
            romlist.append(os.path.splitext(args.gamefile)[0])

    args.roms = romlist

    if ((args.fullshuffle and args.basicshuffle)) or (args.singleshuffle and (args.fullshuffle or args.basicshuffle)):
        parser.print_help()
        sys.exit()

    if args.live and int(args.live) < 1:
        LOGGER.warning("Can't choose live updates shorter than 1 second, defaulting to 1 second")
        args.live = 1

    # When shuffling a single pack, don't auto-extend non-extended packs.
    if (args.singleshuffle):
        args.basicshuffle = True

    main(args)
