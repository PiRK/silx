# coding: utf-8
# /*##########################################################################
#
# Copyright (c) 2004-2016 European Synchrotron Radiation Facility
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
# ###########################################################################*/
"""
This module defines a class :class:`PluginLoader` to handle loading of plugins
from  PLUGINS_DIR.
"""
import os
import sys
import glob
import logging
from collections import OrderedDict

__authors__ = ["V.A. Sole", "P. Knobel"]
__license__ = "MIT"
__date__ = "16/09/2016"


PLUGINS_DIR = None

_logger = logging.getLogger(__name__)


class PluginLoader(object):
    """"Class to handle loading of plugins according to target method.

    On instantiation, this class imports all the plugins found in the PLUGINS_DIR
    directory and stores them into the attribute :attr:`pluginInstanceDict`

    This class is intended to be inherited by plot windows who need to implement
    plugins.
    """
    def __init__(self, method=None, directoryList=None):
        self._pluginDirList = []

        self.pluginInstanceDict = OrderedDict()
        """Ordered dictionary whose keys are plugin module names and
        whose values are plugin objects"""

        self.getPlugins(method=method, directoryList=directoryList)

    def setPluginDirectoryList(self, dirlist):
        """
        :param dirlist: Set directories to search for plugins
        :type dirlist: list
        """
        for directory in dirlist:
            if not os.path.exists(directory):
                raise IOError("Directory:\n%s\ndoes not exist." % directory)
        self._pluginDirList = dirlist

    def getPluginDirectoryList(self):
        """
        :return dirlist: List of directories for searching plugins
        """
        return self._pluginDirList

    def getPlugins(self, method=None, directoryList=None, exceptions=False):
        """
        Import or reloads all the available plugins with the target method

        :param method: The method to be searched for.
        :type method: string, default "getPlugin1DInstance"
        :param directoryList: The list of directories for the search.
        :type directoryList: list or None (default).
        :param exceptions: If True, return the list of error messages
        :type exceptions: boolean (default False)
        :return: The number of plugins loaded. If exceptions is True,
            also the text with the error encountered.
        :rtype: int or (int, str)
        """
        if method is None:
            method = 'getPlugin1DInstance'
        targetMethod = method
        if directoryList in [None, [] ]:
            directoryList = self._pluginDirList
            if directoryList in [None, []]:
                directoryList = [PLUGINS_DIR]
        if DEBUG:
            print("method: %s" % targetMethod)
            print("directoryList: %s" % directoryList)
        exceptionMessage = ""
        self._pluginDirList = directoryList
        self.pluginList = []
        for directory in self._pluginDirList:
            if directory is None:
                continue
            if not os.path.exists(directory):
                raise IOError("Directory:\n%s\ndoes not exist." % directory)

            fileList = glob.glob(os.path.join(directory, "*.py"))

            # prevent unnecessary imports
            moduleList = []
            for fname in fileList:
                if is_plugin_module(fname, targetMethod):
                    moduleList.append(fname)

            for module in moduleList:
                pluginModName = os.path.basename(module)[:-3]
                if directory not in sys.path:
                    sys.path.insert(0, directory)


                try:
                    if pluginModName not in self.pluginInstanceDict:
                        if pluginModName in sys.modules:
                            if hasattr(sys.modules[pluginModName], targetMethod):
                                reload_module(pluginModName)
                            else:
                                __import__(pluginModName)
                    if hasattr(sys.modules[pluginModName], targetMethod):
                        theCall = getattr(sys.modules[pluginModName],
                                          targetMethod)
                        self.pluginInstanceDict[pluginModName] = theCall(self)
                except:
                    exceptionMessage += \
                        "Problem importing module %s\n" % plugin
                    exceptionMessage += "%s\n" % sys.exc_info()[0]
                    exceptionMessage += "%s\n" % sys.exc_info()[1]
                    exceptionMessage += "%s\n" % sys.exc_info()[2]

        if exceptions:
            return len(self.pluginInstanceDict), exceptionMessage
        else:
            return len(self.pluginInstanceDict)

    @property
    def pluginList(self):
        """:attr:`pluginList` is defined as a property returning a list
        with all keys of the ordered dict :attr:`pluginInstanceDict`

        This is done for compatibility with PyMca, that used a regular
        dictionary together with a list to remember the order in which
        plugins are loaded.

        This way we can ensure :attr:`pluginList` is always synchronised
        with :attr:`pluginInstanceDict`.
        """
        _logger.warning("pluginList is deprecated, use " +
                        "pluginInstanceDict.keys() instead")
        return list(self.pluginInstanceDict.keys())


def reload_module(modname):
    """Reload a module by name, handle python 2/3 compatibility."""
    if sys.version.startswith('3'):
        import importlib
        importlib.reload(sys.modules[modname])
    else:
        reload(sys.modules[modname])


def is_plugin_module(fname, plugin_getter="getPlugin1DInstance"):
    """Return True if a file is a plugin module.

    Plugin modules are characterized by the presence of a special function,
    usually :func:`getPlugin1DInstance`

    :param str fname: Name of file we want to check for being a plugin module
    :param str plugin_getter: Name of the function returning a plugin object
        (default "getPlugin1DInstance")
    """
    f = open(fname, 'r')
    for line in f:
        if line.startswith("def"):
            if line.split(" ")[1].startswith(plugin_getter):
                f.close()
                return True
    f.close()
    return False


def main(targetMethod, directoryList):
    loader = PluginLoader()
    n = loader.getPlugins(targetMethod, directoryList)
    print("Loaded %d plugins" % n)
    for m in loader.pluginList:
        print("Module %s" % m)
        module = sys.modules[m]
        if hasattr(module, 'MENU_TEXT'):
            text = module.MENU_TEXT
        else:
            text = os.path.basename(module.__file__)
            if text.endswith('.pyc'):
                text = text[:-4]
            elif text.endswith('.py'):
                text = text[:-3]
        print("\tMENU TEXT: %s" % text)
        methods = loader.pluginInstanceDict[m].getMethods()
        if not len(methods):
            continue
        for method in methods:
            print("\t\t %s" % method)

if __name__ == "__main__":
    if len(sys.argv) > 2:
        targetMethod  = sys.argv[1]
        directoryList = sys.argv[2:len(sys.argv)]
    elif len(sys.argv) > 1:
        targetMethod = None
        directoryList = sys.argv[1:len(sys.argv)]
    else:
        print("Usage: python PluginLoader.py [targetMethod] directory")
    main(targetMethod, directoryList)
