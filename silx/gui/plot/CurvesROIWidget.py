# coding: utf-8
# /*##########################################################################
#
# Copyright (c) 2004-2017 European Synchrotron Radiation Facility
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
"""Widget to handle regions of interest (ROI) on curves displayed in a PlotWindow.

This widget is meant to work with :class:`PlotWindow`.

ROI are defined by :

- A name (`ROI` column)
- A type. The type is the label of the x axis.
  This can be used to apply or not some ROI to a curve and do some post processing.
- The x coordinate of the left limit (`from` column)
- The x coordinate of the right limit (`to` column)
- Raw counts: Sum of the curve's values in the defined Region Of Intereset.

  .. image:: img/rawCounts.png

- Net counts: Raw counts minus background

  .. image:: img/netCounts.png
"""

__authors__ = ["V.A. Sole", "T. Vincent", "H. Payno"]
__license__ = "MIT"
__date__ = "13/03/2018"

from collections import OrderedDict
import logging
import os
import sys
import weakref
import functools
import numpy
from silx.io import dictdump
from silx.utils import deprecation
from silx.utils.weakref import WeakMethodProxy
from .. import icons, qt


_logger = logging.getLogger(__name__)


class CurvesROIWidget(qt.QWidget):
    """Widget displaying a table of ROI information.

    :param parent: See :class:`QWidget`
    :param str name: The title of this widget
    """

    # sigROIWidgetSignal = qt.Signal(object)
    """Signal of ROIs modifications.

    Modification information if given as a dict with an 'event' key
    providing the type of events.

    Type of events:

    - AddROI, DelROI, LoadROI and ResetROI with keys: 'roilist', 'roidict'

    - selectionChanged with keys: 'row', 'col' 'roi', 'key', 'colheader',
      'rowheader'
    """

    sigROISignal = qt.Signal(object)

    def __init__(self, parent=None, name=None, plot=None):
        super(CurvesROIWidget, self).__init__(parent)
        if name is not None:
            self.setWindowTitle(name)
        assert plot is not None
        self.plot = plot
        layout = qt.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        ##############
        self.headerLabel = qt.QLabel(self)
        self.headerLabel.setAlignment(qt.Qt.AlignHCenter)
        self.setHeader()
        layout.addWidget(self.headerLabel)
        ##############
        widgetAllCheckbox = qt.QWidget(parent=self)
        self._showAllCheckBox = qt.QCheckBox("show all ROI",
                                             parent=widgetAllCheckbox)
        widgetAllCheckbox.setLayout(qt.QHBoxLayout())
        spacer = qt.QWidget(parent=widgetAllCheckbox)
        spacer.setSizePolicy(qt.QSizePolicy.Expanding, qt.QSizePolicy.Fixed)
        widgetAllCheckbox.layout().addWidget(spacer)
        widgetAllCheckbox.layout().addWidget(self._showAllCheckBox)
        layout.addWidget(widgetAllCheckbox)
        ##############
        self.roiTable = ROITable(self, plot=plot)
        rheight = self.roiTable.horizontalHeader().sizeHint().height()
        self.roiTable.setMinimumHeight(4 * rheight)
        layout.addWidget(self.roiTable)
        self._roiFileDir = qt.QDir.home().absolutePath()
        self._showAllCheckBox.toggled.connect(self.roiTable.showAllMarkers)
        #################

        hbox = qt.QWidget(self)
        hboxlayout = qt.QHBoxLayout(hbox)
        hboxlayout.setContentsMargins(0, 0, 0, 0)
        hboxlayout.setSpacing(0)

        hboxlayout.addStretch(0)

        self.addButton = qt.QPushButton(hbox)
        self.addButton.setText("Add ROI")
        self.addButton.setToolTip('Create a new ROI')
        self.delButton = qt.QPushButton(hbox)
        self.delButton.setText("Delete ROI")
        self.addButton.setToolTip('Remove the selected ROI')
        self.resetButton = qt.QPushButton(hbox)
        self.resetButton.setText("Reset")
        self.addButton.setToolTip('Clear all created ROIs. We only let the default ROI')

        hboxlayout.addWidget(self.addButton)
        hboxlayout.addWidget(self.delButton)
        hboxlayout.addWidget(self.resetButton)

        hboxlayout.addStretch(0)

        self.loadButton = qt.QPushButton(hbox)
        self.loadButton.setText("Load")
        self.loadButton.setToolTip('Load ROIs from a .ini file')
        self.saveButton = qt.QPushButton(hbox)
        self.saveButton.setText("Save")
        self.loadButton.setToolTip('Save ROIs to a .ini file')
        hboxlayout.addWidget(self.loadButton)
        hboxlayout.addWidget(self.saveButton)
        layout.setStretchFactor(self.headerLabel, 0)
        layout.setStretchFactor(self.roiTable, 1)
        layout.setStretchFactor(hbox, 0)

        layout.addWidget(hbox)

        self.addButton.clicked.connect(self._add)
        self.delButton.clicked.connect(self._del)
        self.resetButton.clicked.connect(self._reset)

        self.loadButton.clicked.connect(self._load)
        self.saveButton.clicked.connect(self._save)
        self.roiTable.sigROITableSignal.connect(self._forward)

        self.currentRoi = self.roiTable.activeRoi
        self.sigROIWidgetSignal = self.roiTable.sigROITableSignal

        self._isInit = False

    @property
    def roiFileDir(self):
        """The directory from which to load/save ROI from/to files."""
        if not os.path.isdir(self._roiFileDir):
            self._roiFileDir = qt.QDir.home().absolutePath()
        return self._roiFileDir

    @roiFileDir.setter
    def roiFileDir(self, roiFileDir):
        self._roiFileDir = str(roiFileDir)

    def setRois(self, roidict, order=None):
        return self.roiTable.setRois(rois, order)

    def getRois(self, order=None):
        return self.roiTable.getRois(order)

    def setMiddleROIMarkerFlag(self, flag=True):
        return self.roiTable.setMiddleRoiMarkerFlag(flag)

    def _add(self):
        """Add button clicked handler"""
        def getNextROIName():
            roiList, roiDict = self.roiTable.getROIListAndDict()
            nrois = len(roiList)
            if nrois == 0:
                return "ICR"
            else:
                for i in range(nrois):
                    i += 1
                    newroi = "newroi %d" % i
                    if newroi not in roiDict.keys():
                        return newroi

        roi = ROI(name=getNextROIName())
        roi._color = 'black' if roi.name == 'ICR' else 'blue'
        roi._draggable = False if roi.name == 'ICR' else True

        if roi.name == "ICR":
            roi.type = "Default"
        else:
            roi.type = self.plot.getXAxis().getLabel()

        xmin, xmax = self.plot.getXAxis().getLimits()
        fromdata = xmin + 0.25 * (xmax - xmin)
        todata = xmin + 0.75 * (xmax - xmin)
        if roi.name == 'ICR':
            fromdata, dummy0, todata, dummy1 = self._getAllLimits()
        roi.fromdata = fromdata
        roi.todata = todata

        self.roiTable.addRoi(roi)

    def _del(self):
        """Delete button clicked handler"""
        self.roiTable.deleteActiveRoi()

    def _forward(self, ddict):
        """Broadcast events from ROITable signal"""
        self.sigROIWidgetSignal.emit(ddict)

    def _reset(self):
        """Reset button clicked handler"""
        self.roiTable.clear()
        self._add()

    def _load(self):
        """Load button clicked handler"""
        dialog = qt.QFileDialog(self)
        dialog.setNameFilters(
            ['INI File  *.ini', 'JSON File *.json', 'All *.*'])
        dialog.setFileMode(qt.QFileDialog.ExistingFile)
        dialog.setDirectory(self.roiFileDir)
        if not dialog.exec_():
            dialog.close()
            return

        # pyflakes bug http://bugs.debian.org/cgi-bin/bugreport.cgi?bug=666494
        outputFile = dialog.selectedFiles()[0]
        dialog.close()

        self.roiFileDir = os.path.dirname(outputFile)
        self.roiTable.load(outputFile)

    def load(self, filename):
        """Load ROI widget information from a file storing a dict of ROI.

        :param str filename: The file from which to load ROI
        """
        self.roiTable.load(filename)

    def _save(self):
        """Save button clicked handler"""
        dialog = qt.QFileDialog(self)
        dialog.setNameFilters(['INI File  *.ini', 'JSON File *.json'])
        dialog.setFileMode(qt.QFileDialog.AnyFile)
        dialog.setAcceptMode(qt.QFileDialog.AcceptSave)
        dialog.setDirectory(self.roiFileDir)
        if not dialog.exec_():
            dialog.close()
            return

        outputFile = dialog.selectedFiles()[0]
        extension = '.' + dialog.selectedNameFilter().split('.')[-1]
        dialog.close()

        if not outputFile.endswith(extension):
            outputFile += extension

        if os.path.exists(outputFile):
            try:
                os.remove(outputFile)
            except IOError:
                msg = qt.QMessageBox(self)
                msg.setIcon(qt.QMessageBox.Critical)
                msg.setText("Input Output Error: %s" % (sys.exc_info()[1]))
                msg.exec_()
                return
        self.roiFileDir = os.path.dirname(outputFile)
        self.save(outputFile)

    def save(self, filename):
        """Save current ROIs of the widget as a dict of ROI to a file.

        :param str filename: The file to which to save the ROIs
        """
        self.roiTable.save(filename)

    def setHeader(self, text='ROIs'):
        """Set the header text of this widget"""
        self.headerLabel.setText("<b>%s<\b>" % text)

    @deprecation.deprecated(replacement="calculateRois",
                            reason="CamelCase convention")
    def calculateROIs(self, *args, **kw):
        self.calculateRois(*args, **kw)

    def calculateRois(self, roiList=None, roiDict=None):
        """Compute ROI information"""
        return self.roiTable.calculateRois()

    def showAllMarkers(self, _show=True):
        self.roiTable.showAllMarkers(_show)

    def _getAllLimits(self):
        """Retrieve the limits based on the curves."""
        curves = self.plot.getAllCurves()
        if not curves:
            return 1.0, 1.0, 100., 100.

        xmin, ymin = None, None
        xmax, ymax = None, None

        for curve in curves:
            x = curve.getXData(copy=False)
            y = curve.getYData(copy=False)
            if xmin is None:
                xmin = x.min()
            else:
                xmin = min(xmin, x.min())
            if xmax is None:
                xmax = x.max()
            else:
                xmax = max(xmax, x.max())
            if ymin is None:
                ymin = y.min()
            else:
                ymin = min(ymin, y.min())
            if ymax is None:
                ymax = y.max()
            else:
                ymax = max(ymax, y.max())

        return xmin, ymin, xmax, ymax


class _FloatItem(qt.QTableWidgetItem):
    def __init__(self):
        qt.QTableWidgetItem.__init__(self, type=qt.QTableWidgetItem.Type)

    def __lt__(self, other):
        if self.text() in ('', ROITable.INFO_NOT_FOUND):
            return False
        if other.text() in ('', ROITable.INFO_NOT_FOUND):
            return True
        return float(self.text()) < float(other.text())


class ROITable(qt.QTableWidget):
    """Table widget displaying ROI information.

    See :class:`QTableWidget` for constructor arguments.
    """

    sigROITableSignal = qt.Signal(object)
    """Signal of ROI table modifications.
    """

    COLUMNS_INDEX = OrderedDict([
        ('ROI', 0),
        ('Type', 1),
        ('From', 2),
        ('To', 3),
        ('Raw Counts', 4),
        ('Net Counts', 5)
    ])

    COLUMNS = list(COLUMNS_INDEX.keys())

    INFO_NOT_FOUND = '????????'

    def __init__(self, parent=None, plot=None, rois=None):
        super(ROITable, self).__init__(parent)
        self.activeRoi = None
        self._showAllMarkers = False
        self._middleROIMarkerFlag = False
        self._RoiToItems = {}
        self.roidict = {}
        self.setColumnCount(len(self.COLUMNS))
        self.setPlot(plot)
        self.__setTooltip()
        self.setSortingEnabled(True)

    def clear(self):
        self._RoiToItems = {}
        qt.QTableWidget.clear(self)
        self.setRowCount(0)
        self.setHorizontalHeaderLabels(self.COLUMNS)
        self.horizontalHeader().setSectionResizeMode(
            qt.QHeaderView.ResizeToContents)
        self.sortByColumn(2, qt.Qt.AscendingOrder)

    def setPlot(self, plot):
        self.clear()
        self.plot = plot

    def __setTooltip(self):
        self.horizontalHeaderItem(self.COLUMNS_INDEX['ROI']).setToolTip(
            'Region of interest identifier')
        self.horizontalHeaderItem(self.COLUMNS_INDEX['Type']).setToolTip(
            'Type of the ROI')
        self.horizontalHeaderItem(self.COLUMNS_INDEX['From']).setToolTip(
            'X-value of the min point')
        self.horizontalHeaderItem(self.COLUMNS_INDEX['To']).setToolTip(
            'X-value of the max point')
        self.horizontalHeaderItem(self.COLUMNS_INDEX['Raw Counts']).setToolTip(
            'Estimation of the integral between y=0 and the selected curve')
        self.horizontalHeaderItem(self.COLUMNS_INDEX['Net Counts']).setToolTip(
            'Estimation of the integral between the segment [maxPt, minPt] '
            'and the selected curve')

    def setRois(self, rois, order=None):
        """Set the ROIs by providing a dictionary of ROI information.

        The dictionary keys are the ROI names.
        Each value is a sub-dictionary of ROI info with the following fields:

        - ``"from"``: x coordinate of the left limit, as a float
        - ``"to"``: x coordinate of the right limit, as a float
        - ``"type"``: type of ROI, as a string (e.g "channels", "energy")


        :param roidict: Dictionary of ROIs
        :param str order: Field used for ordering the ROIs.
             One of "from", "to", "type".
             None (default) for no ordering, or same order as specified
             in parameter ``roidict`` if provided as an OrderedDict.
        """
        assert order in [None, "from", "to", "type"]
        self.clear()
        for roi in rois:
            _roi = roi
            if isinstance(roi, weakref.ref):
                _roi = _roi()
            if _roi:
                assert isinstance(roi, _ROI)
                self.addRoi(roi)

    def addRoi(self, roi):
        """
        TODO

        :param roi: 
        :return: 
        """
        assert isinstance(roi, ROI)
        self.setRowCount(self.rowCount() + 1)
        indexTable = self.rowCount() - 1

        self._RoiToItems[roi.name] = self._getItem('ROI', indexTable, roi)
        self.roidict[roi.name] = roi
        self.activeRoi = roi
        self._updateRoiInfo(roi.name)
        callback = functools.partial(WeakMethodProxy(self._updateRoiInfo),
                                     roi.name)
        roi.sigChanged.connect(callback)

    def _getItem(self, name, row, roi):
        item = self.item(row, self.COLUMNS_INDEX[name])
        if item:
            return item
        else:
            if name == 'ROI':
                item = qt.QTableWidgetItem(roi.name if roi else '',
                                               type=qt.QTableWidgetItem.Type)
                if roi.name.upper() in ('ICR', 'DEFAULT'):
                    item.setFlags(qt.Qt.ItemIsSelectable | qt.Qt.ItemIsEnabled)
                else:
                    item.setFlags(qt.Qt.ItemIsSelectable |
                                      qt.Qt.ItemIsEnabled |
                                      qt.Qt.ItemIsEditable)
            elif name == 'Type':
                item = qt.QTableWidgetItem(type=qt.QTableWidgetItem.Type)
                item.setFlags((qt.Qt.ItemIsSelectable | qt.Qt.ItemIsEnabled))
            elif name == 'To':
                item = _FloatItem()
                item.setFlags(qt.Qt.ItemIsSelectable |
                              qt.Qt.ItemIsEnabled |
                              qt.Qt.ItemIsEditable)
            elif name == 'From':
                item = _FloatItem()
                item.setFlags(qt.Qt.ItemIsSelectable |
                              qt.Qt.ItemIsEnabled |
                              qt.Qt.ItemIsEditable)
            elif name in ('Raw Counts', 'Net Counts'):
                item = _FloatItem()
            else:
                raise ValueError('item type not recognized')

            self.setItem(row, self.COLUMNS_INDEX[name], item)
            return item

    def deleteActiveRoi(self):
        """
        TODO
        
        :return: 
        """
        activeItem = self.selectedItems()
        if len(activeItem) is 0:
            return
        roiToRm = set()
        for item in activeItem:
            row = item.row()
            itemName = self.item(row, 0)
            roiToRm.add(itemName.text())
        [self.removeROI(roiName) for roiName in roiToRm]

    def removeROI(self, name):
        """
        TODO
        
        :param name: 
        :return: 
        """
        if name in self._RoiToItems:
            item = self._RoiToItems[name]
            self.removeRow(item.row())
            del self._RoiToItems[name]

            assert name in self.roidict
            del self.roidict[name]

    def _computeRawAndNetCounts(self, roi):
        assert isinstance(roi, ROI)
        if not self.plot:
            return None, None

        activeCurve = self.plot.getActiveCurve(just_legend=False)
        if activeCurve is None:
            return None, None

        x = activeCurve.getXData(copy=False)
        y = activeCurve.getYData(copy=False)
        idx = numpy.argsort(x, kind='mergesort')
        xproc = numpy.take(x, idx)
        yproc = numpy.take(y, idx)

        # update from and to only in the case of the non editable 'ICR' ROI
        if roiName == 'ICR':
            # TODO : limit on the visible effect
            roi.fromdata = xproc.min()
            roi.todata = xproc.max()

        idx = numpy.nonzero((roi.fromdata <= xproc) & (xproc <= roi.todata))[0]
        if len(idx):
            xw = xproc[idx]
            yw = yproc[idx]
            rawCounts = yw.sum(dtype=numpy.float)
            deltaX = xw[-1] - xw[0]
            deltaY = yw[-1] - yw[0]
            if deltaX > 0.0:
                slope = (deltaY / deltaX)
                background = yw[0] + slope * (xw - xw[0])
                netCounts = (rawCounts -
                             background.sum(dtype=numpy.float))
            else:
                netCounts = 0.0
            return rawCounts, netCounts
        else:
            return 0.0, 0.0

    def setActiveRoi(self, roi):
        """
        TODO
        
        :param roi: 
        :return: 
        """
        assert isinstance(roi, ROI)
        if roi.name in self._RoiToItems.keys():
            self.activeRoi = roi
            self.selectRow(self._RoiToItems[roi.name].row())

    def _updateRoiInfo(self, roiName):
        if roiName not in self.roidict:
            return
        roi = self.roidict[roiName]
        assert roi.name in self._RoiToItems

        itemName = self._RoiToItems[roi.name]
        itemType = self._getItem(name='Type', row=itemName.row(), roi=roi)
        itemType.setText(roi.type or self.INFO_NOT_FOUND)

        itemFrom = self._getItem(name='From', row=itemName.row(), roi=roi)
        fromdata = str(roi.fromdata) if roi.fromdata is not None else self.INFO_NOT_FOUND
        itemFrom.setText(fromdata)

        itemTo = self._getItem(name='To', row=itemName.row(), roi=roi)
        todata = str(roi.todata) if roi.todata is not None else self.INFO_NOT_FOUND
        itemTo.setText(todata)

        self._computeRawAndNetCounts(roi)
        itemRawCounts = self._getItem(name='Raw Counts', row=itemName.row(),
                                      roi=roi)
        rawCounts = str(roi._rawCounts) if roi._rawCounts is not None else self.INFO_NOT_FOUND
        itemRawCounts.setText(rawCounts)

        itemNetCounts = self._getItem(name='Net Counts', row=itemName.row(),
                                      roi=roi)
        netCounts = str(roi._netCounts) if roi._netCounts is not None else self.INFO_NOT_FOUND
        itemNetCounts.setText(netCounts)

    def currentChanged(self, current, previous):
        if previous and current.row() != previous.row():
            # note: roi is registred as a weak ref

            roiItem = self.item(current.row(), self.COLUMNS_INDEX['ROI'])
            assert roiItem
            self.activeRoi = self.roidict[roiItem.text()]
            self._updateMarkers()
        qt.QTableWidget.currentChanged(self, current, previous)

    def getROIListAndDict(self):
        """
        TODO
        
        :return: 
        """
        return list(self.roidict.values()), self.roidict

    def calculateRois(self, roiList=None, roiDict=None):
        """
        TODO
        
        :param roiList: 
        :param roiDict: 
        :return: 
        """
        if roiDict:
            from silx.utils.deprecation import deprecated_warning
            deprecated_warning(name=roiDict, type='Parameter',
                               reason='Unused parameter', since_version="0.8.0")
        if roiList:
            from silx.utils.deprecation import deprecated_warning
            deprecated_warning(name=roiList, type='Parameter',
                               reason='Unused parameter', since_version="0.8.0")

        for roiName in self.roidict:
            self._updateRoiInfo(roiName)

    # def showEvent(self, event):
    #     self._visibilityChangedHandler(visible=True)
    #     qt.QWidget.showEvent(self, event)
    #
    # def hideEvent(self, event):
    #     self._visibilityChangedHandler(visible=False)
    #     qt.QWidget.hideEvent(self, event)

    def _visibilityChangedHandler(self, visible):
        """Handle widget's visibility updates.

        It is connected to plot signals only when visible.
        """
        if visible:
            if not self._isInit:
                # Deferred ROI widget init finalization
                self._finalizeInit()
            if not self._isConnected:
                self.plot.sigPlotSignal.connect(self._handleROIMarkerEvent)
                self.plot.sigActiveCurveChanged.connect(
                    self._activeCurveChanged)
                self._isConnected = True

                self.calculateRois()
        else:
            if self._isConnected:
                self.plot.sigPlotSignal.disconnect(self._handleROIMarkerEvent)
                self.plot.sigActiveCurveChanged.disconnect(
                    self._activeCurveChanged)
                self._isConnected = False

    def _updateMarkers(self):
        self._clearMarkers()
        if self._showAllMarkers is True:
            if self._middleROIMarkerFlag:
                self.plot.remove('ROI middle', kind='marker')
            roiList, roiDict = self.getROIListAndDict()

            for roi in roiDict:
                fromdata = roiDict[roi].fromdata
                todata = roiDict[roi].todata
                _name = roi
                _nameRoiMin = _name + ' ROI min'
                _nameRoiMax = _name + ' ROI max'
                self.plot.addXMarker(fromdata,
                                     legend=_nameRoiMin,
                                     text=_nameRoiMin,
                                     color=roiDict[roi]._color,
                                     draggable=roiDict[roi]._draggable)
                self.plot.addXMarker(todata,
                                     legend=_nameRoiMax,
                                     text=_nameRoiMax,
                                     color=roiDict[roi]._color,
                                     draggable=roiDict[roi]._draggable)

        else:
            if not self.activeRoi or not self.plot:
                return
            assert isinstance(self.activeRoi, ROI)
            self.plot.addXMarker(self.activeRoi.fromdata,
                                 legend='ROI min',
                                 text='ROI min',
                                 color=self.activeRoi._color,
                                 draggable=self.activeRoi._draggable)
            self.plot.addXMarker(self.activeRoi.todata,
                                 legend='ROI max',
                                 text='ROI max',
                                 color=self.activeRoi._color,
                                 draggable=self.activeRoi._draggable)
            if self.activeRoi._draggable and self._middleROIMarkerFlag:
                pos = 0.5 * (fromdata + todata)
                self.plot.addXMarker(pos,
                                     legend='ROI middle',
                                     text="",
                                     color='yellow',
                                     draggable=self.activeRoi._draggable)

    def _clearMarkers(self):
        if not self.plot:
            return
        self.plot.remove('ROI min', kind='marker')
        self.plot.remove('ROI max', kind='marker')
        self.plot.remove('ROI middle', kind='marker')

        roilist, roidict = self.getROIListAndDict()
        for roi in roidict:
            _name = roi
            _nameRoiMin = _name + ' ROI min'
            _nameRoiMax = _name + ' ROI max'
            self.plot.remove(_nameRoiMin, kind='marker')
            self.plot.remove(_nameRoiMax, kind='marker')

    def getRois(self, order, asDict=False):
        """
        Return the currently defined ROIs, as an ordered dict.

        The dictionary keys are the ROI names.
        Each value is a :class:`ROI` object..
        
        :param order: Field used for ordering the ROIs.
             One of "from", "to", "type", "netcounts", "rawcounts".
             None (default) to get the same order as displayed in the widget.
        :return: Ordered dictionary of ROI information
        """

        roilist, roidict = self.roiTable.getROIListAndDict()
        if order is None or order.lower() == "none":
            ordered_roilist = roilist
        else:
            assert order in ["from", "to", "type", "netcounts", "rawcounts"]
            ordered_roilist = sorted(roidict.keys(),
                                     key=lambda roi_name: roidict[roi_name].get(order))

        return OrderedDict([(name, roidict[name]) for name in ordered_roilist])

    def save(self, filename):
        """
        Save current ROIs of the widget as a dict of ROI to a file.

        :param str filename: The file to which to save the ROIs
        """
        self.roiTable.save(filename)
        _roilist, _roidict = self.roiTable.getROIListAndDict()
        roilist = []
        roidict = {}
        for roi in _roilist:
            roilist.append(roi.toDict())
            roidict[roi.name] = roi.toDict()
        datadict = {'ROI': {'roilist': roilist, 'roidict': roidict}}
        dictdump.dump(datadict, filename)

    def load(self, filename):
        """
        Load ROI widget information from a file storing a dict of ROI.

        :param str filename: The file from which to load ROI
        """
        roisDict = dictdump.load(filename)
        rois = []

        # Remove rawcounts and netcounts from ROIs
        for roiDict in roisDict['ROI']['roidict'].values():
            roiDict.pop('rawcounts', None)
            roiDict.pop('netcounts', None)
            rois.append(ROI._frmDict(roiDict))

        self.roiTable.setRois(rois)

    def showAllMarkers(self, _show=True):
        """
        TODO
        :param _show: 
        :return: 
        """
        if self._showAllMarkers == _show:
            return

        self._showAllMarkers = _show
        self._updateMarkers()

    def setMiddleROIMarkerFlag(self, flag=True):
        """
        Activate or deactivate middle marker.

        This allows shifting both min and max limits at once, by dragging
        a marker located in the middle.

        :param bool flag: True to activate middle ROI marker
        """
        self._middleROIMarkerFlag = flag


class ROI(qt.QObject):

    sigChanged = qt.Signal()

    def __init__(self, name, fromdata=None, todata=None):
        qt.QObject.__init__(self)
        assert type(name) is str
        self.name = name
        self.fromdata = fromdata
        self.todata = todata
        self._marker = None
        self._draggable = False
        self._color = 'blue'
        self.type = 'Default'
        self._rawCounts = None
        self._netCounts = None

    def toDict(self):
        return {
            'type': self.type,
            'name': self.name,
            'from': self.fromdata,
            'to': self.todata,
        }


class CurvesROIDockWidget(qt.QDockWidget):
    """QDockWidget with a :class:`CurvesROIWidget` connected to a PlotWindow.

    It makes the link between the :class:`CurvesROIWidget` and the PlotWindow.

    :param parent: See :class:`QDockWidget`
    :param plot: :class:`.PlotWindow` instance on which to operate
    :param name: See :class:`QDockWidget`
    """
    sigROISignal = qt.Signal(object)
    """Deprecated signal for backward compatibility with silx < 0.7.
    Prefer connecting directly to :attr:`CurvesRoiWidget.sigRoiSignal`
    """

    def __init__(self, parent=None, plot=None, name=None):
        super(CurvesROIDockWidget, self).__init__(name, parent)

        assert plot is not None
        self.plot = plot
        self.roiWidget = CurvesROIWidget(self, name, plot=plot)
        """Main widget of type :class:`CurvesROIWidget`"""

        # convenience methods to offer a simpler API allowing to ignore
        # the details of the underlying implementation
        # (ALL DEPRECATED)
        self.calculateROIs = self.calculateRois = self.roiWidget.calculateRois
        self.setRois = self.roiWidget.setRois
        self.getRois = self.roiWidget.getRois
        self.roiWidget.sigROISignal.connect(self._forwardSigROISignal)
        self.currentROI = self.roiWidget.currentRoi

        self.layout().setContentsMargins(0, 0, 0, 0)
        self.setWidget(self.roiWidget)

    def _forwardSigROISignal(self, ddict):
        # emit deprecated signal for backward compatibility (silx < 0.7)
        self.sigROISignal.emit(ddict)

    def toggleViewAction(self):
        """Returns a checkable action that shows or closes this widget.

        See :class:`QMainWindow`.
        """
        action = super(CurvesROIDockWidget, self).toggleViewAction()
        action.setIcon(icons.getQIcon('plot-roi'))
        return action

    def showEvent(self, event):
        """Make sure this widget is raised when it is shown
        (when it is first created as a tab in PlotWindow or when it is shown
        again after hiding).
        """
        self.raise_()
        qt.QDockWidget.showEvent(self, event)

    def _handleROIMarkerEvent(self, ddict):
        """Handle plot signals related to marker events."""
        if ddict['event'] == 'markerMoved':

            label = ddict['label']
            if label not in ['ROI min', 'ROI max', 'ROI middle']:
                return

            roiList, roiDict = self.roiTable.getROIListAndDict()
            if self.currentRoi is None:
                return
            if self.currentRoi not in roiDict:
                return
            x = ddict['x']

            if label == 'ROI min':
                roiDict[self.currentRoi]['from'] = x
                if self._middleROIMarkerFlag:
                    pos = 0.5 * (roiDict[self.currentRoi]['to'] +
                                 roiDict[self.currentRoi]['from'])
                    self.plot.addXMarker(pos,
                                         legend='ROI middle',
                                         text='',
                                         color='yellow',
                                         draggable=True)
            elif label == 'ROI max':
                roiDict[self.currentRoi]['to'] = x
                if self._middleROIMarkerFlag:
                    pos = 0.5 * (roiDict[self.currentRoi]['to'] +
                                 roiDict[self.currentRoi]['from'])
                    self.plot.addXMarker(pos,
                                         legend='ROI middle',
                                         text='',
                                         color='yellow',
                                         draggable=True)
            elif label == 'ROI middle':
                delta = x - 0.5 * (roiDict[self.currentRoi]['from'] +
                                   roiDict[self.currentRoi]['to'])
                roiDict[self.currentRoi]['from'] += delta
                roiDict[self.currentRoi]['to'] += delta
                self.plot.addXMarker(roiDict[self.currentRoi]['from'],
                                     legend='ROI min',
                                     text='ROI min',
                                     color='blue',
                                     draggable=True)
                self.plot.addXMarker(roiDict[self.currentRoi]['to'],
                                     legend='ROI max',
                                     text='ROI max',
                                     color='blue',
                                     draggable=True)
            else:
                return
            self.calculateRois(roiList, roiDict)
            self._emitCurrentROISignal()