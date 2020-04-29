import time
from pprint import pprint

class StatusMediaListener:
    def __init__(self, name, cast, mc, yt):
        self.name = name
        self.cast = cast
        self.playing = mc.status.title
        self.yt = yt

    def new_media_status(self, status):
        if status.title != self.playing:
            print(status.title,self.playing)
            self.playing = status.title
            print(self.yt.get_session_data())
