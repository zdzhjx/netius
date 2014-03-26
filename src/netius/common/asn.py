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

import types

import netius

import util

INTEGER = 0x02
BIT_STRING = 0x03
OCTET_STRING = 0x04
NULL = 0x05
OBJECT_IDENTIFIER = 0x06
SEQUENCE = 0x30

ASN1_OBJECT = [
    (SEQUENCE, [
        (SEQUENCE, [
            OBJECT_IDENTIFIER,
            NULL
        ]),
        BIT_STRING
    ])
]

ASN1_RSA_PUBLIC_KEY = [
    (SEQUENCE, [
        INTEGER,
        INTEGER
    ])
]

ASN1_RSA_PRIVATE_KEY = [
    (SEQUENCE, [
        INTEGER,
        INTEGER,
        INTEGER,
        INTEGER,
        INTEGER,
        INTEGER,
        INTEGER,
        INTEGER,
        INTEGER
    ])
]

def asn1_parse(template, data):
    """
    Parse a data structure according to ASN.1 template,
    the provided template should respect the predefined
    structure. The provided data is going to be validated
    against the template format and a exception raised in
    case the data is not conformant.

    @type template: List/Tuple
    @param template: A list of tuples comprising the ASN.1 template.
    @type: List
    @param data: A list of bytes to parse.
    """

    result = []
    index = 0

    for item in template:
        # verifies if the data type for the current template
        # item to be parser is tuple and based on that defined
        # the current expected data type and children values
        is_tuple = type(item) == types.TupleType
        if is_tuple: dtype, children = item
        else: dtype = item; children = None

        # retrieves the value (as an ordinal) for the current
        # byte and increments the index for the parser
        tag = ord(data[index])
        index += 1

        # in case the current type is not of the expect type,
        # must raise an exception indicating the problem to
        # the top level layers (should be properly handled)
        if not tag == dtype:
            raise netius.ParserError("Unexpected tag (got 0x%02x, expecting 0x%02x)" % (tag, dtype))

        # retrieves the ordinal value of the current byte as
        # the length of the value to be parsed and then increments
        # the pointer of the buffer reading process
        length = ord(data[index])
        index += 1

        # in case the last bit of the length byte is set the,
        # the byte designates the length of the byte sequence that
        # defines the length of the current value to be read instead
        if length & 0x80:
            number = length & 0x7f
            length = util.bytes_to_integer(data[index:index + number])
            index += number

        if tag == INTEGER:
            number = util.bytes_to_integer(data[index:index + length])
            index += length
            result.append(number)

        elif tag == BIT_STRING:
            result.append(data[index:index + length])
            index += length

        elif tag == NULL:
            assert length == 0
            result.append(None)

        elif tag == OBJECT_IDENTIFIER:
            result.append(data[index:index + length])
            index += length

        elif tag == SEQUENCE:
            part = asn1_parse(children, data[index:index + length])
            result.append(part)
            index += length

        else:
            raise netius.ParserError("Unexpected tag in template 0x%02x" % tag)

    return result

def asn1_length(length):
    """
    Returns a string representing a field length in ASN.1 format.
    This value is computed taking into account the multiple byte
    representation of very large values.

    @type length: int
    @param length:The integer based length value that is going to
    be used in the conversion to a string representation.
    @rtype: String
    @return: The string based representation of the provided length
    integer value according to the ASN.1 specification.
    """

    assert length >= 0
    if length < 0x7f: return chr(length)

    result = util.integer_to_bytes(length)
    number = len(result)
    result = chr(number | 0x80) + result
    return result

def asn_gen(node):
    generator = asn1_build(node)
    return "".join(generator)

def asn1_build(node):
    """
    Builds an ASN.1 data structure based on pairs of (type, data),
    this function may be used as a generator of a buffer.

    @type node: Tuple
    @param node: The root node of the structure that is going to be
    used as reference for the generation of the ASN.1 buffer.
    """

    tag, value = node

    if tag == OCTET_STRING:
        yield chr(OCTET_STRING) + asn1_length(len(value)) + value

    elif tag == INTEGER:
        value = util.integer_to_bytes(value)
        yield chr(INTEGER) + asn1_length(len(value)) + value

    elif tag == NULL:
        assert value is None
        yield chr(NULL) + asn1_length(0)

    elif tag == OBJECT_IDENTIFIER:
        yield chr(OBJECT_IDENTIFIER) + asn1_length(len(value)) + value

    elif tag == SEQUENCE:
        buffer = []
        for item in value:
            generator = asn1_build(item)
            data = "".join(generator)
            buffer.append(data)
        result = "".join(buffer)
        yield chr(SEQUENCE) + asn1_length(len(result)) + result

    else:
        raise netius.GeneratorError("Unexpected tag in template 0x%02x" % tag)