__all__ = [
    "dispatcher",
]

import asyncore

import inotify


class dispatcher(asyncore.file_dispatcher):
    """ Subclasses can monitor inotify watch events by overriding the
        handle_watch(event) method. """

    def __init__(self, flags=0, bufsize=65536, map=None):
        """ Initialize an inotify event queue and register it with
            asyncore.  flags is passed to inotify.init().  bufsize is
            used when receiving events."""

        fd = inotify.init(flags)
        asyncore.file_dispatcher.__init__(self, fd, map)
        self.bufsize = bufsize

    def add_watch(self, name, mask):
        """ Calls inotify.add_watch() for the event queue. """

        return inotify.add_watch(self.socket.fileno(), name, mask)

    def rm_watch(self, wd):
        """ Calls inotify.rm_watch() for the event queue. """

        inotify.rm_watch(self.socket.fileno(), wd)

    def handle_watch(self, event):
        """ Process your watch events here.  event is an inotify.event
            class instance."""

        self.log_info("unhandled watch event", "warning")

    def handle_read(self):
        buf = self.recv(self.bufsize)
        if buf:
            for event in inotify.unpack_events(buf):
                self.handle_watch(event)
        else:
            self.close()

    def writable(self):
        return False
