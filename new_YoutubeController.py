import pychromecast
from pychromecast.controllers.youtube import YouTubeController
from casttube import YouTubeSession
import json

YOUTUBE_BASE_URL = "https://www.youtube.com/"
BIND_URL = YOUTUBE_BASE_URL + "api/lounge/bc/bind"
LOUNGE_TOKEN_URL = YOUTUBE_BASE_URL + "api/lounge/pairing/get_lounge_token_batch"
QUEUE_AJAX_URL = YOUTUBE_BASE_URL + "watch_queue_ajax"

HEADERS = {"Origin": YOUTUBE_BASE_URL, "Content-Type": "application/x-www-form-urlencoded"}
LOUNGE_ID_HEADER = "X-YouTube-LoungeId-Token"
REQ_PREFIX = "req{req_id}"

WATCH_QUEUE_ITEM_CLASS = 'yt-uix-scroller-scroll-unit watch-queue-item'
GSESSION_ID_REGEX = '"S","(.*?)"]'
SID_REGEX = '"c","(.*?)",\"'

CURRENT_INDEX = "_currentIndex"
CURRENT_TIME = "_currentTime"
AUDIO_ONLY = "_audioOnly"
VIDEO_ID = "_videoId"
LIST_ID = "_listId"
ACTION = "__sc"
COUNT = "count"

ACTION_SET_PLAYLIST = "setPlaylist"
ACTION_CLEAR = "clearPlaylist"
ACTION_REMOVE = "removeVideo"
ACTION_INSERT = "insertVideo"
ACTION_ADD = "addVideo"
ACTION_GET_QUEUE_ITEMS = "action_get_watch_queue_items"

GSESSIONID = "gsessionid"
LOUNGEIDTOKEN = "loungeIdToken"
CVER = "CVER"
TYPE = "TYPE"
RID = "RID"
SID = "SID"
VER = "VER"
AID = "AID"
CI = "CI"

BIND_DATA = {"device": "REMOTE_CONTROL", "id": "aaaaaaaaaaaaaaaaaaaaaaaaaa", "name": "Python",
             "mdx-version": 3, "pairing_type": "cast", "app": "android-phone-13.14.55"}


class YouTubeSession(YouTubeSession):
    def get_session_data(self):
        """
        Get data about the current active session using an xmlhttp request.
        :return: List of session attributes
        """
        url_params = {LOUNGEIDTOKEN: self._lounge_token, VER: 8, "v": 2, RID: "rpc", SID: self._sid,
                      GSESSIONID: self._gsession_id, TYPE: "xmlhttp", "t": 1, AID: 5, CI: 1}
        url_params.update(BIND_DATA)
        response = self._do_post(BIND_URL, headers={LOUNGE_ID_HEADER: self._lounge_token},
                                 session_request=True, params=url_params)
        response_text = response.text
        response_text = response_text.replace("\n", "")
        try:
            response_list = json.loads(response_text[response_text.find("["):])
        except:
            print()
            print("error!!")
            print(response_text)
            response_list = self.get_session_data()
        # response_now_playing = next(v[1] for k, v in response_list if v[0]=='nowPlaying')
        return response_text


class YouTubeController(YouTubeController):
    def start_session_if_none(self):
        """
        Starts a session it is not yet initialized.
        """
        if not (self._screen_id and self._session):
            self.update_screen_id()
            self._session = YouTubeSession(screen_id=self._screen_id)

    def init_session(self):
        self.start_session_if_none()
        self._session._start_session()

    def get_session_data(self):
        self.start_session_if_none()
        self._session._start_session()
        return self._session.get_session_data()
