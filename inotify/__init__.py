__all__ = [
    "CLOEXEC",
    "NONBLOCK",

    "ACCESS",
    "MODIFY",
    "ATTRIB",
    "CLOSE_WRITE",
    "CLOSE_NOWRITE",
    "CLOSE",
    "OPEN",
    "MOVED_FROM",
    "MOVED_TO",
    "MOVE",
    "CREATE",
    "DELETE",
    "DELETE_SELF",
    "MOVE_SELF",
    "UNMOUNT",
    "Q_OVERFLOW",
    "IGNORED",
    "ONLYDIR",
    "DONT_FOLLOW",
    "ADD_MASK",
    "ISDIR",
    "ONESHOT",
    "ALL_EVENTS",

    "event",

    "init",
    "add_watch",
    "rm_watch",
    "unpack_event",
    "unpack_events",
]

import ctypes
import ctypes.util
import errno
import os
import select
import struct

CLOEXEC = 0o02000000
NONBLOCK = 0o00004000

ACCESS = 0x00000001
MODIFY = 0x00000002
ATTRIB = 0x00000004
CLOSE_WRITE = 0x00000008
CLOSE_NOWRITE = 0x00000010
CLOSE = CLOSE_WRITE | CLOSE_NOWRITE
OPEN = 0x00000020
MOVED_FROM = 0x00000040
MOVED_TO = 0x00000080
MOVE = MOVED_FROM | MOVED_TO
CREATE = 0x00000100
DELETE = 0x00000200
DELETE_SELF = 0x00000400
MOVE_SELF = 0x00000800
UNMOUNT = 0x00002000
Q_OVERFLOW = 0x00004000
IGNORED = 0x00008000
ONLYDIR = 0x01000000
DONT_FOLLOW = 0x02000000
ADD_MASK = 0x20000000
ISDIR = 0x40000000
ONESHOT = 0x80000000
ALL_EVENTS = ACCESS | MODIFY | ATTRIB | CLOSE | OPEN | MOVE | CREATE | DELETE | DELETE_SELF | MOVE_SELF


class event(object):
    """ See inotify(7) man page. """

    __slots__ = (
        "wd",
        "mask",
        "cookie",
        "name",
    )

    def __init__(self, wd, mask, cookie, name):
        self.wd = wd
        self.mask = mask
        self.cookie = cookie
        self.name = name

    def __repr__(self):
        return "inotify.event(wd=%d, mask=0x%x, cookie=%d, name=%r)" % (self.wd, self.mask, self.cookie, self.name)


def errcheck(result, func, arguments):
    if result < 0:
        n = ctypes.get_errno()
        raise OSError(n, os.strerror(n))

    return result


libc = ctypes.CDLL(ctypes.util.find_library("c"), use_errno=True)

try:
    libc.inotify_init1
except AttributeError:
    libc.inotify_init.argtypes = []
    libc.inotify_init.errcheck = errcheck  # type: ignore

    def init(flags=0):
        """ See inotify_init(2) man page. """

        assert flags == 0
        return libc.inotify_init()
else:
    libc.inotify_init1.argtypes = [ctypes.c_int]
    libc.inotify_init1.errcheck = errcheck  # type: ignore

    def init(flags=0):
        """ See inotify_init1(2) man page. """

        return libc.inotify_init1(flags)

libc.inotify_add_watch.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_uint32]
libc.inotify_add_watch.errcheck = errcheck  # type: ignore


def add_watch(fd, name, mask):
    """ See inotify_add_watch(2) man page. """

    return libc.inotify_add_watch(fd, name.encode(), mask)


libc.inotify_rm_watch.argtypes = [ctypes.c_int, ctypes.c_int]
libc.inotify_rm_watch.errcheck = errcheck  # type: ignore


def rm_watch(fd, wd):
    """ See inotify_rm_watch(2) man page. """

    libc.inotify_rm_watch(fd, wd)


def unpack_event(buf):
    """ Returns the first event from buf and the rest of the buf. """

    headsize = 16

    wd, mask, cookie, namesize = struct.unpack("iIII", buf[:headsize])
    name = buf[headsize:headsize + namesize]

    if isinstance(name, str):
        name = name.rstrip("\0")
    else:
        n = len(name)
        while n > 0 and name[n - 1] == 0:
            n -= 1
        name = name[:n]

    ev = event(wd, mask, cookie, name or None)
    buf = buf[headsize + namesize:]

    return ev, buf


def unpack_events(buf):
    """ Returns the events from buf as a list. """

    events = []

    while buf:
        ev, buf = unpack_event(buf)
        events.append(ev)

    return events


class Instance(object):

    def __init__(self, flags=0):
        self.fd = init(flags)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def __iter__(self):
        while True:
            try:
                r, _, _ = select.select([self.fd], [], [])
            except select.error as e:
                if e.args[0] == errno.EINTR:
                    continue
                raise

            if r:
                for event in self.read_events():
                    yield event

    def add_watch(self, name, mask):
        return add_watch(self.fd, name, mask)

    def rm_watch(self, wd):
        rm_watch(self.fd, wd)

    def read_events(self, bufsize=65536):
        return unpack_events(os.read(self.fd, bufsize))

    def close(self):
        if self.fd is not None:
            try:
                os.close(self.fd)
            finally:
                self.fd = None
