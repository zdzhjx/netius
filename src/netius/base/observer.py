#!/usr/bin/python
# -*- coding: utf-8 -*-

# Hive Netius System
# Copyright (C) 2008-2012 Hive Solutions Lda.
#
# This file is part of Hive Netius System.
#
# Hive Netius System is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Hive Netius System is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Hive Netius System. If not, see <http://www.gnu.org/licenses/>.

__author__ = "João Magalhães joamag@hive.pt>"
""" The author(s) of the module """

__version__ = "1.0.0"
""" The version of the module """

__revision__ = "$LastChangedRevision$"
""" The revision number of the module """

__date__ = "$LastChangedDate$"
""" The last change date of the module """

__copyright__ = "Copyright (c) 2008-2012 Hive Solutions Lda."
""" The copyright for the module """

__license__ = "GNU General Public License (GPL), Version 3"
""" The license for the module """

class Observable(object):
    """
    The base class that implements the observable
    patter allowing the object to handle a series of
    event in a dynamic fashion.

    This class should be friendly to multiple inheritance
    and should avoid variable naming collision.
    """

    def __init__(self, *args, **kwargs):
        self.events = {}

    def __del__(self):
        self.unbind_all()

    def build(self):
        pass

    def destroy(self):
        self.unbind_all()

    def bind(self, name, method):
        methods = self.events.get(name, [])
        methods.append(method)
        self.events[name] = methods

    def unbind(self, name, method = None):
        methods = self.events.get(name, None)
        if not methods: return
        if method: methods.remove(method)
        else: del methods[:]

    def unbind_all(self):
        if not hasattr(self, "_events"): return
        for methods in self.events.itervalues(): del methods[:]
        self.events.clear()

    def trigger(self, name, *args, **kwargs):
        methods = self.events.get(name, None)
        if not methods: return
        for method in methods: method(*args, **kwargs)
