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
"""Command line interface to execute the main() functions in any silx module.

This version uses ``os.walk`` to find a list of all ``.py`` and ``.so`` files
in directories containing a __init__.py file.

A module name can be specified as a long name (e.g silx.gui.plot.PlotWindow),
or as a short name (eg PlotWindow if there is no ambiguity).


usage: runmodule_oswalk.py [-h] [-l] [-s SEARCH] [module] ...

positional arguments:
  module                Module name whose main() function you want to run
  mainargs              Additional arguments for the module's main() function

optional arguments:
  -h, --help            Show a help message and exit
  -l, --list-modules    List all available modules and exit
  -s SEARCH, --search SEARCH
                        List modules containing the specified SEARCH string
                        and exit
"""

__authors__ = ["P. Knobel"]
__license__ = "MIT"
__date__ = "11/05/2016"

import argparse
import os
import sys
from importlib import import_module

import silx

##############################################################################
# Parse command line arguments
##############################################################################

parser = argparse.ArgumentParser(description='Interface script for silx',
                                 add_help=False)
parser.add_argument('module',
                    help='Module name whose main() function you want to run',
                    nargs="?")
parser.add_argument('mainargs', nargs=argparse.REMAINDER,
                    help="Additional arguments for the module's main() function")
# we overwrite the -h option to be able to print a module specific message
parser.add_argument("-h", "--help", action="store_true",
                    help="Show a help message and exit")
parser.add_argument("-l", "--list-modules", action="store_true",
                    help="List all available modules and exit")
parser.add_argument("-s", "--search",
    help="List modules containing the specified SEARCH string and exit")

args = parser.parse_args()

if args.module is None:
    if args.help:
        parser.print_help()
        sys.exit()
    elif not args.list_modules and args.search is None:
        parser.print_help()
        print("Error: too few arguments")
        print("You must supply a valid module name or one option (-h -l -s)")
        sys.exit(2)

##############################################################################
# Get list of all modules
# We fill two list, one with complete module names including namespace, and
# another one with short name (after the last .)
##############################################################################

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

##############################################################################
# Display available modules if -l/--list-modules was specified
##############################################################################
if args.list_modules:
    print("Available modules:")
    for modname in sorted(longmodnames):
        print(modname)
    sys.exit()

##############################################################################
# Display available modules if -s/--search was specified
##############################################################################
if args.search is not None:
    print("Modules containing '%s':" % args.search)
    for modname in sorted(longmodnames):
        if args.search in modname:
            print("\t" + modname)
    sys.exit()

##############################################################################
# Check that command line arguments correspond to an existing non-ambiguous
# module name
##############################################################################
if args.module in longmodnames:
    longmodname = args.module
elif args.module in shortmodnames:
    if shortmodnames.count(args.module) > 1:
        found_modules = [mod for mod in longmodnames if mod.endswith(args.module)]
        print("Ambiguous module name '%s', found %d candidates: %s" %
              (args.module, shortmodnames.count(args.module),
               str(found_modules)))
        print("Try again using the complete module name")
        sys.exit(2)
    longmodname = longmodnames[shortmodnames.index(args.module)]
else:
    print("No module " + args.module + " found")
    print("Use -l to list all available modules")
    print("Use -s %s to search module names containing '%s'" % (args.module, args.module))
    sys.exit(2)

##############################################################################
# Import module, check the presence of a main() function
##############################################################################

m = import_module(longmodname)

if not 'main' in dir(m):
    print("Error: Module %s does not have a main() function" % longmodname)
    sys.exit(1)

##############################################################################
# Display help and exit if -h/--help was specified
##############################################################################
if args.help:
    if m.main.__doc__ is None or m.main.__doc__.strip() == "":
        print("%s.main does not have a docstring" % longmodname)
    else:
        print(m.main.__doc__)
    sys.exit()

##############################################################################
# Import the module and run the main function
##############################################################################

try:
    # the signature of m.main() should be `int main(*argv)`
    status = m.main(*args.mainargs)
except TypeError:
    print("Error: wrong number of arguments for the main() function")
    if m.main.__doc__ is not None:
        print("Docstrinq of %s.main:" % longmodname)
        print(m.main.__doc__)
    sys.exit(1)

# if status is an int, it is considered an exit status
# (0 for success, 1 for general errors, 2 for command line syntax error)
# None is equivalent to 0, any other object is printed to stderr and results
# in an exit code of 1
sys.exit(status)



