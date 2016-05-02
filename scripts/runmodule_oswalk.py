# coding: utf-8
#/*##########################################################################
# Copyright (C) 2016 European Synchrotron Radiation Facility
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#
#############################################################################*/
"""Command line interface to execute main() functions in silx modules.

This version uses ``os.walk`` to find a list of all ``.py`` and ``.so`` files.
This has the advantage of not needing to import all packages."""

__authors__ = ["P. Knobel"]
__license__ = "MIT"
__date__ = "02/05/2016"

import argparse
import os
import sys
from importlib import import_module

import silx

parser = argparse.ArgumentParser(description='Interface script for silx')
parser.add_argument('command',
                    help='module name whose main() function you want to run')
parser.add_argument('mainargs', nargs='*',
                    help='arguments passed to the main() function')

args = parser.parse_args()

longmodnames = []
silx_path = silx.__path__[0]

for dirpath, _, filelist in os.walk(silx_path):
    if "__init__.py" in filelist:
        modfilelist = [fname for fname in filelist if
                       fname.endswith(".py") or fname.endswith(".so")]
        for fname in modfilelist:
            if fname == "__init__.py":
                # module name is the dir name
                modpath = dirpath
                modname = modpath.replace(silx_path, "silx").replace(os.sep, ".")
            else:
                # module name is the file name without the extension
                modpath = os.path.join(dirpath, fname)
                modname = modpath.replace(silx_path, "silx").replace(os.sep, ".")[:-3]

            longmodnames.append(modname)

shortmodnames = [modname.split(".")[-1] for modname in longmodnames]

if args.command in longmodnames:
    longmodname = args.command
elif args.command in shortmodnames:
    if shortmodnames.count(args.command) > 1:
        found_modules = [mod for mod in longmodnames if mod.endswith(args.command)]
        print("Ambiguous module name '%s', found %d candidates: %s" %
              (args.command, shortmodnames.count(args.command),
               str(found_modules)))
        print("Try again using the complete module name")
        sys.exit(2)
    longmodname = longmodnames[shortmodnames.index(args.command)]
else:
    print("No module " + args.command + " found")
    print("Available modules:")
    print(longmodnames)
    sys.exit(2)

m = import_module(longmodname)
main = getattr(m, "main")

# the signature of main() should be `int main(*argv)`
status = main(*args.mainargs)

# if status is an int, it is considered an exit status
# (0 for success, 1 for general errors, 2 for command line syntax error…)
# None is equivalent to 0, any other object is printed to stderr and results
# in an exit code of 1
sys.exit(status)


