# ================================= MoodleExport =========================================
# this software is released under the GNU GPL v3.0 license, more info in the LICENSE file
# GitHub repo: https://github.com/AlexF1789/MoodleExport
# ======================================================================================== 

# main.py -> this script is the main script, it relays on the Classes.py script to work

from Classes import Exporter
import argparse

# configuration of the argument parser for the command line
parser = argparse.ArgumentParser(description="script used to export Moodle quiz attempts")
parser.add_argument("file", help="instruction file given you from Moodle web interface", type=str)

# we parse the arguments
args = parser.parse_args()

# we export according to the file content, not passing an argument for max_workers means we're using 2*os.cpu_count()
exp = Exporter(args.file)
exp.execute_commands()