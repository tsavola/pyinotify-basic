import asyncore
import logging
import os

import inotify
import inotify.async

class TestDispatcher(inotify.async.dispatcher):

	def handle_watch(self, event):
		print(id(self), event)

	def handle_error(self):
		logging.exception(id(self))
		self.close()

def main():
	d = TestDispatcher(inotify.CLOEXEC)
	d.add_watch("/tmp", inotify.ALL_EVENTS)
	d.add_watch("/dev", inotify.ALL_EVENTS & ~inotify.ACCESS)

	d = TestDispatcher(inotify.NONBLOCK)
	d.add_watch(os.getenv("HOME"), inotify.ALL_EVENTS)

	asyncore.loop()

if __name__ == "__main__":
	main()
