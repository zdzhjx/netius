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

import math
import uuid
import time
import types
import struct
import hashlib

import netius.common
import netius.clients

ID_STRING = "NE1000"
""" Text value that is going to be used to identify the agent
of torrent against the other peers, should be a join of both
the abbreviation of the agent name and version """

BLOCK_SIZE = 16384
""" The typical size of block that is going to be retrieved
using the current torrent infra-structure, this value conditions
most of the torrent operations and should be defined carefully """

class Pieces(netius.Observable):
    """
    Class that represents the logical structure of a file that is
    divided into pieces and blocks as a hierarchy, this class is
    responsible for the management of the data structures of such
    data storage model.
    """

    def __init__(self, owner, number_pieces, number_blocks):
        netius.Observable.__init__(self)

        self.owner = owner
        self.number_pieces = number_pieces
        self.number_blocks = number_blocks
        self.bitfield = [True for _index in xrange(number_pieces)]
        self.mask = [True for _index in xrange(number_pieces * number_blocks)]

    def pop_block(self, bitfield):
        index = 0
        result = self._and(bitfield, self.bitfield)
        for bit in result:
            if bit == True: break
            index += 1

        if index == len(result): return None

        begin = self.update_block(index)
        return (index, begin)

    def mark_block(self, index, begin):
        base = index * self.number_blocks
        block_index = begin / BLOCK_SIZE
        self.mask[base + block_index] = False
        self.trigger("block", self, index, begin)
        self.update_piece(index)

    def update_block(self, index):
        base = index * self.number_blocks

        for block_index in xrange(self.number_blocks):
            state = self.mask[base + block_index]
            if state == True: break

        begin = block_index * BLOCK_SIZE
        self.mark_block(index, begin)
        return begin

    def update_piece(self, index):
        base = index * self.number_blocks
        piece_state = False

        for block_index in xrange(self.number_blocks):
            state = self.mask[base + block_index]
            if state == False: continue
            piece_state = True
            break

        self.bitfield[index] = piece_state
        if piece_state == False: self.trigger("piece", self, index)

    def _and(self, first, second):
        result = []
        for _first, _second in zip(first, second):
            if _first and _second: value = True
            else: value = False
            result.append(value)
        return result

class TorrentTask(netius.Observable):
    """
    Describes a task (operation) that is going to be performed
    using the peer to peer mesh network of the torrent protocol.

    Each of the download operations should be able to be described
    by this task object (for latter reference).
    """

    def __init__(self, owner, target_path, torrent_path = None, info_hash = None):
        netius.Observable.__init__(self)

        self.owner = owner
        self.target_path = target_path
        self.start = time.time()
        self.uploaded = 0
        self.downloaded = 0
        self.left = 0
        self.peers = []

        if torrent_path: self.info = self.load_info(torrent_path)
        else: self.info = dict(info_hash = info_hash)

        self.pieces_tracker()
        self.peers_tracker()

        self.load_file()
        self.load_pieces()

    def load_info(self, torrent_path):
        file = open(torrent_path, "rb")
        try: data = file.read()
        finally: file.close()

        struct = netius.common.bdecode(data)
        struct["info_hash"] = netius.common.info_hash(struct)
        return struct


    def on_block(self, task, index, begin):
        self.trigger("block", self, index, begin)

    def on_piece(self, task, index):
        self.verify_piece(index)
        self.trigger("piece", self, index)

    def load_file(self):
        self.file = open(self.target_path, "wb")
        self.file.seek(780140544 - 1)
        self.file.write("\0")
        self.file.flush()

    def load_pieces(self):
        number_pieces = self.info["number_pieces"]
        number_blocks = self.info["number_blocks"]
        self.requested = Pieces(self, number_pieces, number_blocks)
        self.stored = Pieces(self, number_pieces, number_blocks)
        self.stored.bind("block", self.on_block)
        self.stored.bind("piece", self.on_piece)

    def pieces_tracker(self):
        info = self.info.get("info", {})
        pieces = info.get("pieces", "")
        piece_length = info.get("piece length", 1)
        number_blocks = math.ceil(float(piece_length) / float(BLOCK_SIZE))
        number_blocks = int(number_blocks)
        self.info["pieces"] = [piece for piece in netius.common.chunks(pieces, 20)]
        self.info["number_pieces"] = len(self.info["pieces"])
        self.info["number_blocks"] = number_blocks

    def set_data(self, data, index, begin):
        piece_length = self.info["info"]["piece length"]
        self.file.seek(index * piece_length + begin)
        self.file.write(data)
        self.file.flush()
        self.stored.mark_block(index, begin)
        self.downloaded += len(data)

    def peers_tracker(self):
        """
        Tries to retrieve as much information as possible about the
        peers from the currently loaded tracker information.

        It's possible that no tracker information exits for the current
        task and for such situations no state change will occur.
        """

        # retrieves both the announce and the announce list structure from
        # the current info dictionary and uses both of them to create the
        # final list containing the various addresses of trackers, then
        # iterates over each of the trackers to retrieve the information
        # about the various peers associated with the torrent file
        announce = self.info.get("announce", None)
        announce_list = self.info.get("announce-list", [[announce]])
        for tracker in announce_list:
            tracker_url = tracker[0]
            result = netius.clients.HTTPClient.get_s(
                tracker_url,
                params = dict(
                    info_hash = self.info["info_hash"],
                    peer_id = self.owner.peer_id,
                    port = "1000",
                    uploaded = self.uploaded,
                    downloaded = self.downloaded,
                    left = self.left,
                    compact = "0"
                ),
                async = False
            )

            data = result["data"]
            if not data: continue

            response = netius.common.bdecode(data)
            peers = response["peers"]

            if type(peers) == types.DictType:
                self.peers = peers
                continue

            peers = [peer for peer in netius.common.chunks(peers, 6)]
            for peer in peers:
                address, port = struct.unpack("!LH", peer)
                ip = netius.common.addr_to_ip4(address)
                peer = dict(
                    ip = ip,
                    port = port
                )
                self.peers.append(peer)

    def connect_peers(self):
        for peer in self.peers: self.connect_peer(peer)

    def connect_peer(self, peer):
        self.owner.client.peer(self, peer["ip"], peer["port"])

    def speed(self):
        """
        Retrieves a float number representing the global speed
        of the task in bytes per second, this value is computed
        using the original creation time of the task and so it
        may not represent the most accurate speedup.

        @rtype: float
        @return: The current speed of download, defined as bytes
        per second from the original task creation time.
        """

        current = time.time()
        delta = current - self.start
        bytes_second = self.downloaded / delta
        return bytes_second

    def pop_block(self, bitfield):
        return self.requested.pop_block(bitfield)

    def verify_piece(self, index):
        file = open(self.target_path, "rb")
        try: self._verify_piece(index, file)
        finally: file.close()

    def _verify_piece(self, index, file):
        piece = self.info["pieces"][index]
        piece_length = self.info["info"]["piece length"]
        file = open(self.target_path, "rb")
        file.seek(index * piece_length)
        pending = piece_length
        hash = hashlib.sha1()
        while True:
            if pending == 0: break
            count = BLOCK_SIZE if pending > BLOCK_SIZE else pending
            data = file.read(count)
            hash.update(data)
            pending -= count
        digest = hash.digest()
        if digest ==  piece: return
        raise netius.DataError("Verifying piece index '%d'" % index)

class TorrentServer(netius.StreamServer):

    def __init__(self, *args, **kwargs):
        netius.StreamServer.__init__(self, *args, **kwargs)
        self.peer_id = self._generate_id()
        self.client = netius.clients.TorrentClient(*args, **kwargs)

    def download(self, target_path, torrent_path = None, info_hash = None):
        """
        Starts the "downloading" process of a torrent associated file
        using the defined peer to peer torrent strategy suing either
        the provided torrent path as reference or just the info hash
        of the file that is going to be downloaded.

        Note that if only the info hash is provided a DHT bases strategy
        is going to be used to retrieve the peers list.

        The returned value is the task entity representing the newly created
        task for the downloading of the requested file, this object may be
        used for the operations and listening of events.

        @type target_path: String
        @param target_path: The path to the file that will be used to store
        the binary information resulting from the download, this file may also
        be used to store some temporary information on state of download.
        @type torrent_path: String
        @param torrent_path: The path to the file that contains the torrent
        information that is going to be used for file processing.
        @type info_hash: String
        @param info_hash: The info hash value of the file that is going
        to be downloaded, may be used for magnet torrents (DHT).
        @rtype: TorrentTask
        @return: The torrent task object that represents the task that has been
        created for downloading of the requested file.
        """

        task = TorrentTask(
            self,
            target_path,
            torrent_path = torrent_path,
            info_hash = info_hash
        )
        task.connect_peers()
        return task

    def _generate_id(self):
        random = str(uuid.uuid4())
        hash = hashlib.sha1(random)
        digest = hash.hexdigest()
        id = "-%s-%s" % (ID_STRING, digest[:12])
        return id

if __name__ == "__main__":
    def on_piece(task, index):
        speed = task.speed()
        speed_s = netius.common.size_round_unit(speed)
        print "%s/s" % speed_s

    torrent_server = TorrentServer()
    task = torrent_server.download("C:/tobias.download", "C:\ubuntu.torrent")
    task.bind("piece", on_piece)
    torrent_server.serve(env = True)
