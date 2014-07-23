#!/usr/bin/python
# -*- coding: utf-8 -*-

# Hive Netius System
# Copyright (C) 2008-2014 Hive Solutions Lda.
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

__author__ = "João Magalhães <joamag@hive.pt>"
""" The author(s) of the module """

__version__ = "1.0.0"
""" The version of the module """

__revision__ = "$LastChangedRevision$"
""" The revision number of the module """

__date__ = "$LastChangedDate$"
""" The last change date of the module """

__copyright__ = "Copyright (c) 2008-2014 Hive Solutions Lda."
""" The copyright for the module """

__license__ = "GNU General Public License (GPL), Version 3"
""" The license for the module """

import inspect

import logging.handlers

def rotating_handler(
    path = "netius.log",
    max_bytes = 1048576,
    max_log = 5,
    encoding = None,
    delay = False
):
    return logging.handlers.RotatingFileHandler(
        path,
        maxBytes = max_bytes,
        backupCount = max_log,
        encoding = encoding,
        delay = delay
    )

def smtp_handler(
    host = "localhost",
    port = 25,
    sender = "no-reply@netius.com",
    receivers = [],
    subject = "Netius logging",
    username = None,
    password = None,
    stls = False
):
    address = (host, port)
    if username and password: credentials = (username, password)
    else: credentials = None
    has_secure = in_signature(logging.handlers.SMTPHandler.__init__, "secure")
    if has_secure: kwargs = dict(secure = () if stls else None)
    else: kwargs = dict()
    return logging.handlers.SMTPHandler(
        address,
        sender,
        receivers,
        subject,
        credentials = credentials,
        **kwargs
    )

def in_signature(callable, name):
    spec = inspect.getargspec(callable)
    args = spec[0]; kwargs = spec[2]
    return (args and name in args) or (kwargs and "secure" in kwargs)
