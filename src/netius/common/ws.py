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

__author__ = "João Magalhães joamag@hive.pt>"
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

import netius

def encode_ws(data):
    data = netius.bytes(data)
    data_l = len(data)

    encoded_l = list()
    encoded_l.append(netius.chr(129))

    if data_l <= 125:
        encoded_l.append(netius.chr(data_l))

    elif data_l >= 126 and data_l <= 65535:
        encoded_l.append(netius.chr(126))
        encoded_l.append(netius.chr((data_l >> 8) & 255))
        encoded_l.append(netius.chr(data_l & 255))

    else:
        encoded_l.append(netius.chr(127))
        encoded_l.append(netius.chr((data_l >> 56) & 255))
        encoded_l.append(netius.chr((data_l >> 48) & 255))
        encoded_l.append(netius.chr((data_l >> 40) & 255))
        encoded_l.append(netius.chr((data_l >> 32) & 255))
        encoded_l.append(netius.chr((data_l >> 24) & 255))
        encoded_l.append(netius.chr((data_l >> 16) & 255))
        encoded_l.append(netius.chr((data_l >> 8) & 255))
        encoded_l.append(netius.chr(data_l & 255))

    encoded_l.append(data)
    encoded = b"".join(encoded_l)
    return encoded

def decode_ws(data):
    # retrieves the reference to the second byte in the frame
    # this is the byte that is going to be used in the initial
    # calculus of the length for the current data frame
    second_byte = data[1]

    # retrieves the base length (simplified length) of the
    # frame as the seven last bits of the second byte in frame
    length = netius.ord(second_byte) & 127
    index_mask_f = 2

    # verifies if the length to be calculated is of type
    # extended (length equals to 126) if that's the case
    # two extra bytes must be taken into account on length
    if length == 126:
        length = 0
        length += netius.ord(data[2]) << 8
        length += netius.ord(data[3])
        index_mask_f = 4

    # check if the length to be calculated is of type extended
    # payload length and if that's the case many more bytes
    # (eight) must be taken into account for length calculus
    elif length == 127:
        length = 0
        length += netius.ord(data[2]) << 56
        length += netius.ord(data[3]) << 48
        length += netius.ord(data[4]) << 40
        length += netius.ord(data[5]) << 32
        length += netius.ord(data[6]) << 24
        length += netius.ord(data[7]) << 16
        length += netius.ord(data[8]) << 8
        length += netius.ord(data[9])
        index_mask_f = 10

    # calculates the size of the raw data part of the message and
    # in case its smaller than the defined length of the data returns
    # immediately indicating that there's not enough data to complete
    # the decoding of the data (should be re-trying again latter)
    raw_size = len(data) - index_mask_f - 4
    if raw_size < length:
        raise netius.DataError("Not enough data available for parsing")

    # retrieves the masks part of the data that are going to be
    # used in the decoding part of the process
    masks = data[index_mask_f:index_mask_f + 4]

    # allocates the array that is going to be used
    # for the decoding of the data with the length
    # that was computed as the data length
    decoded_a = bytearray(length)

    # starts the initial data index and then iterates over the
    # range of decoded length applying the mask to the data
    # (decoding it consequently) to the created decoded array
    i = index_mask_f + 4
    for j in range(length):
        decoded_a[j] = netius.chri(netius.ord(data[i]) ^ netius.ord(masks[j % 4]))
        i += 1

    # converts the decoded array of data into a string and
    # and returns the "partial" string containing the data that
    # remained pending to be parsed
    decoded = bytes(decoded_a)
    return decoded, data[i:]
