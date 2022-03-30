# Command-line description

Log Level: `--loglevel`
: Set up logging
: Default: `info`
: _Example_: `warning` to cancel default logging

MSU Pack Collection root: `--collection`
: Root folder to search for packs in, relative to script folder
: Default: `..`

Game Track Number Manifest: `--game`
: Default: `snes\zelda3`
: (results in using `.\resources\snes\zelda3\manifests\tracks.json`)
: _Example_: `[platform]\[gameSlug]`
: (results in using `.\resources\[platform]\[gameSlug]\manifests\tracks.json`)

Game file to patch: `--gamefile`
: Default: `*.sfc`

Output path for game file and music pack: `--outputpath`
: Default: `.\shuffled*`

Output prefix for game file and music pack: `--outputprefix`
: Default: `shuffled`
: _Example_:
  : Game File: `[outputpath]\[outputprefix].sfc`
  : Dummy MSU File: `[outputpath]\[outputprefix].msu`
  : Track Files: `[outputpath]\[outputprefix]-[trackNum].pcm`

Copy Game File for patching: `--copy`
: Copy Game File for patching instead of overwriting source game file
: Default: `False`

`--fullshuffle`
: fullshuffle

`--basicshuffle`
: basicshuffle

Single Shuffle: `--singleshuffle`
: Grab tracks from one MSU pack; MSU pack folder to search in, relative to script folder
: Default: Empty string

`--higan`
: higan is a special cupcake and likes stuff sorted in a special way. This executes ~~Order 66~~ a higan-flavored file structure.

`--realcopy`
: realcopy

`--dry-run`
: Do a Dry Run. Talk about what would happen instead of actually doing it.

`--verbose`
: Extra output in info messages.

`--live`
: Live Shuffle. Continue shuffling on an interval to keep it fresh.

`--version`
: Print Version for debug purposes

Z3M3 assumes _A Link to the Past_ packs in `./zelda3` and _Super Metroid_ packs in `./metroid3`

```py
py Main.py --game=snes/zelda3   --gamefile=zelda3-msu.sfc
py Main.py --game=snes/metroid3 --gamefile=metroid3-msu.sfc
py Main.py --game=snes/z3m3     --gamefile=z3m3-msu.sfc
```
