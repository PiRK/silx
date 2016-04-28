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

This version uses pkgutil.walk_packages to find a list of all modules. 
This means that all modules are imported (can be an issue in case of circular
import)."""

__authors__ = ["P. Knobel"]
__license__ = "MIT"
__date__ = "28/04/2016"

import argparse
import pkgutil
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
for importer, modname, ispkg in pkgutil.walk_packages(
                                            path=silx.__path__,
                                            prefix=silx.__name__+ '.',
                                            onerror=lambda x: None):
    longmodnames.append(modname)


print(longmodnames)

shortmodnames = [modname.split(".")[-1] for modname in longmodnames]

if args.command in longmodnames:
    longmodname = args.command
elif args.command in shortmodnames:
    if shortmodnames.count(args.command) > 1:
        print("Ambiguous module name: " + args.command)
        print("Found %d modules with this name" % shortmodnames.count(args.command))
        sys.exit(1)
    longmodname = longmodnames[shortmodnames.index(args.command)]
else:
    print("No module " + args.command + " found")
    print("Available modules:")
    print(longmodnames)
    sys.exit(2)

print("Running module " + longmodname)
m = import_module(longmodname)
main = getattr(m, "main")
main(*args.mainargs)


