# coding: utf-8
# /*##########################################################################
#
# Copyright (c) 2017 European Synchrotron Radiation Facility
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
Calibration classes.
"""
import numpy


class CalibrationBase(object):
    def __init__(self, label=None, unit=None):
        """
        :param str label: Optional label associated with the calibrated axis.
        :param str unit: Optional unit associated with the calibrated axis.
        """
        super(CalibrationBase, self).__init__()

        self.label = label
        """Optional Label associated with calibrated axis"""
        self.unit = unit
        """Optional unit associated with calibrated axis
        (e.g. "keV", "°C"...)"""


class LinearCalibration(CalibrationBase):
    """Linear calibration class

    :param 2-tuple coefficients: *(a, b)* tuple of coefficients
        characterising the linear calibration
        ``x_calib = a * x + b``
    :param str label: Optional label associated with the calibrated axis.
    :param str unit: Optional unit associated with the calibrated axis.
    """
    def __init__(self, coefficients, label=None, unit=None):
        """
        """
        super(LinearCalibration, self).__init__(label=label, unit=unit)

        self.coefficients = coefficients
        """2-tuple *(a, b)* used for the linear calibration of an axis
        ``calibrated_axis = a * axis + b``
        """

        self._slope = coefficients[0]
        self._y_intercept = coefficients[1]

    def calibrate(self, axis):
        """
        Return linearly calibrated axis using coefficients in
        :attr:`coefficients`.

        :param axis: Axis (1D array)
        """
        return self._slope * axis + self._y_intercept

    def calibrateRanges(self, length):
        """Return default axis linearly calibrated.

        Default axis is *numpy.arange(length)*.

        :param int length: Length (number of values) of the default axis.
        :return: self.calibrate(numpy.arange(length))
        """
        self.calibrate(numpy.arange(length))

    def __call__(self, axis):
        """
        """
        if isinstance(axis, int):
            return self.calibrateRanges(axis)
        return self.calibrate(axis)
