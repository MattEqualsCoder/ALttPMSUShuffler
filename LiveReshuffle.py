import os
import time
# Helper script for reshuffling a MSU-1 pack every few seconds; works well
# when using MSU packs with emulators, allowing you to experience different
# music whenever the track is next loaded after being reshuffled.
#
# See Main.py for full documentation.

# Number of seconds to wait between reshuffles of the MSU pack
INTERVAL = 900

os.system(f"ECHO Live Reshuffler set to {INTERVAL} seconds")
while True:
    os.system(f"py main.py --game=\"snes/z3m3\" --collection=\"..\\snes\\z3m3\"")
    os.system("ECHO Tracks have been shuffled")
    time.sleep(INTERVAL)
