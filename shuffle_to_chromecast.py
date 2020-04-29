import logging
import random
from main import get_available_client, update_client_status, youtube_authentication

import pychromecast
from pychromecast.controllers.youtube import YouTubeController

CAST_IP = '192.168.1.194'
PLAYLIST_ID = "PLM7k3j7Jzfe_yYIywL0khAV0ZTTedvuLh"
MAX_NUM_OF_VIDEOS = 50

def get_video_ids(youtube):
    video_ids = []
    is_last_page = False
    page_token = ""
    while not(is_last_page):
        request = youtube.playlistItems().list(
            part="contentDetails",
            maxResults=50,
            pageToken=page_token,
            playlistId = PLAYLIST_ID
        )
        response = request.execute()
        try:
            page_token = response["nextPageToken"]
        except KeyError:
            is_last_page = True
        video_ids += [item["contentDetails"]["videoId"] for item in response["items"]]
    random.shuffle(video_ids)
    return video_ids[:min(MAX_NUM_OF_VIDEOS,len(video_ids))]

def setup_chromecast(cast, video_ids):
    cast.wait()
    print(cast.device)
    print(cast.status)
    print("====================================")

    yt = YouTubeController()
    cast.register_handler(yt)
    yt.play_video(video_ids[0])
    i = 1
    print(f"{i} song added.")
    for video_id in video_ids[1:]:
        yt.add_to_queue(video_id)
        i += 1
        print(f"{i} song added.")

if __name__ == "__main__":
    available_client = get_available_client()
    logging.getLogger('googleapiclient.discovery_cache').setLevel(logging.ERROR)
    logging.getLogger('googleapiclient.http').setLevel(logging.ERROR)

    try:
        # cast = find_chromecast()
        cast = pychromecast.Chromecast(CAST_IP)
        youtube  = youtube_authentication(available_client)
        video_ids = get_video_ids(youtube)
        setup_chromecast(cast, video_ids)

    except Exception as e:
        if not (str(e).startswith('<HttpError 403 when requesting ') & \
                (str(e).endswith(
                    ' returned "The request cannot be completed because you have exceeded your <a href="/youtube/v3/getting-started#quota">quota</a>.">') |
                 (
                         ' returned "Daily Limit Exceeded. The quota will be reset at midnight Pacific Time (PT). You may monitor your quota usage and adjust limits in the API Console: ' in str(
                     e)))):
            raise
        else:
            update_client_status(available_client)
            print("\n==================================\n")
            print(f"Quota for Client {available_client} is used up.")