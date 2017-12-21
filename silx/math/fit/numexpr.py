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
# ############################################################################*/
"""
This module provides fit tools using the
`*numexpr* library <https://numexpr.readthedocs.io/en/latest/api.html>`_.

.. warning::

    *numexpr* is an optional dependency of *silx*. An *ImportError* will be
    raised when importing this module if *numexpr* is not installed.

"""
__authors__ = ["P. Knobel"]
__license__ = "MIT"
__date__ = "21/12/2017"
__copyright__ = "European Synchrotron Radiation Facility, Grenoble, France"

try:
    import numexpr
except ImportError:
    raise ImportError("numexpr must be installed, to use silx.math.fit.numexpr")

from .leastsq import leastsq


def numexpr_to_model(expr):
    """Take a numexpr containing any number of variables,
    *x* being one of them, and return a function with the
    signature ``f(x, *args)``, where *args* is a list of all
    the remaining parameters after removing *x*.

    Except for *x*, the parameters remain in the same order
    as they appear in the numexpr.

    For example::

        f = numexpr_to_model("a*x*x + b*cos(x -c)")

    is equivalent to::

        def f(x, a, b, c):
            return a*x*x + b*cos(x -c)

    :param str expr: Numerical expression. See https://numexpr.readthedocs.io/en/latest/api.html
    :return: Function f(x, *args)
    :raise: SyntaxError if numexpr cannot be parsed, or if no *x* variable
        can be found in numexpr.
    """
    try:
        num_expr = numexpr.NumExpr(expr)
    except Exception as e:
        raise SyntaxError("Could not construct numexpr from expression "
                          "'%s'. " % expr +
                          "Numexpr error message: %s" % e)
    param_list = list(num_expr.input_names)
    if "x" in param_list:
        x_idx_in_params = param_list.index("x")
    else:
        raise SyntaxError("No x parameter found in numexpr '%s'." % expr)

    def f(x, *args):
        # insert x in the expected position
        pars = list(args)
        pars.insert(x_idx_in_params, x)
        return num_expr(*pars)

    return f


def fit_numexpr(expr, *args, **kwargs):
    """Use non-linear least squares Levenberg-Marquardt algorithm to fit a function
    defined by a *numexpr*.

    This is a convenience function wrapping :func:`silx.math.fit.leastsq`.

    :param str expr: Numerical expression, containing the variable *x*.
         See https://numexpr.readthedocs.io/en/latest/api.html

    :param args: See :func:`silx.math.fit.leastsq`. Don't provide *model*.
    :return:  See :func:`silx.math.fit.leastsq`.
    """
    # TODO: return format (named parameters as dict...)
    model = numexpr_to_model(expr)
    return leastsq(model, *args, **kwargs)

# TODO: module name different from library name
# doc for optional dependency in installation manual
