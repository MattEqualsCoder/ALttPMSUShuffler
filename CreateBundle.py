import json, glob, os
from pathlib import Path
parent_path = os.path.dirname(os.path.realpath(__file__))
types = []
json_files = []
for filename in glob.iglob(parent_path + "/resources/snes/**/tracks.json", recursive=True):
    json_files.append(filename)
json_files.sort()
for filename in json_files: # filter dirs
    f = open(filename)
    data = json.load(f)
    parent = Path(filename).parent.parent
    data['meta']['path'] = "snes/" + parent.name
    types.append(data)
    f.close()
f = open(parent_path + "/msu_types.json", "w")
f.write(json.dumps(types, indent=2)+"\r\n")
f.close()
