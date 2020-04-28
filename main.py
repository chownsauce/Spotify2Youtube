# -*- coding: utf-8 -*-
"""
- Obtain Youtube Data API Credentials
    - Create new project at: https://console.developers.google.com/apis/dashboard
    - Enable 'YouTube Data API v3'
    - Create OAuth consent screen
    - Create OAuth client ID
    - Download JSON for the client ID
    - Save JSON in client_serets/CLIENT_SECRET{number}
    - Create client_serets/client_status.txt to store expiration time of credentials:
        e.g. 2020-04-24 13:19:31


- Obtain Spotify API Credentials
    - Create new project at: https://developer.spotify.com/dashboard/
    - Add "http://localhost:8080" to "Redirect URIs"
    - Save spotify_client_id and spotify_client_secret to client_secrets/spotify_secret.py

- Directory structure
    Spotify2Youtube/
    ├── main.py
    ├── history/
    │   └──spotify_username-spotify_playlist-youtube_username.csv
    └── client_secrets/
        ├── CLIENT_SECRET0.json
        ├── CLIENT_SECRET1.json
        ├── client_status.txt
        └── spotify_secret.py
"""

import pandas as pd
import datetime
import logging
from pprint import pprint

import spotipy
from client_secrets.spotify_secret import spotify_client_id, spotify_client_secret

import os
import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors

# spotify settings
SPOTIFY_PLAYLIST_URL = "spotify:playlist:37i9dQZEVXbMDoHDwVN2tF"    # playlist to be converted

def get_tracks():
    scope = 'user-library-read'
    playlist_uri = SPOTIFY_PLAYLIST_URL

    sp_oauth = spotipy.SpotifyOAuth(
        client_id=spotify_client_id,
        client_secret=spotify_client_secret,
        redirect_uri='http://localhost:8080',
        scope=scope,
        show_dialog=False,
        cache_path=".cache.json"
    )
    token_info = sp_oauth.get_cached_token()
    if not token_info:
        code = sp_oauth.get_auth_response()
        token = sp_oauth.get_access_token(code, as_dict=False)
    else:
        token = token_info["access_token"]

    if token:
        sp = spotipy.Spotify(auth=token)
        song_titles = []
        song_uri = []
        artists = []
        time_added = []
        playlist_name = (sp.playlist(playlist_uri)['name'])
        playlist_owner_name = sp.playlist(playlist_uri)['owner']['display_name']
        results = sp.playlist_tracks(playlist_uri)
        def append_track_details(song_titles, song_uri, artists, time_added, playlist_track):
            if playlist_track["track"] is not None:
                date, time = playlist_track['added_at'].split("T")
                date = ''.join(date.split("-"))
                time = ''.join(time[:-1].split(":"))
                time_added.append(date + time)
                track = playlist_track["track"]
                song_uri.append(track['uri'])
                artists.append(track['artists'][0]['name'])
                song_titles.append(track['name'])

        for playlist_track in results["items"]:
            append_track_details(song_titles, song_uri, artists, time_added, playlist_track)

        while results['next']:
            results = sp.next(results)
            for playlist_track in results["items"]:
                append_track_details(song_titles, song_uri, artists, time_added, playlist_track)
        return pd.DataFrame({"Spotify Id" : song_uri, "Track": song_titles, "Artist": artists, "Added Date" : time_added}), playlist_name, playlist_owner_name
    else:
        print("Can't get token")

def get_available_client():
    client_status = open("client_secrets/client_status.txt", "r").read().splitlines()
    available_client = 0
    now = datetime.datetime.now()
    for line in client_status:
        time = datetime.datetime.strptime(line, '%Y-%m-%d %H:%M:%S')
        if (now-time).total_seconds() > 86400:
            print(f"Client {available_client} is available.")
            return available_client
        else:
            available_client += 1
    print("No available client.")
    quit()

def update_client_status(current_client):
    client_status = open("client_secrets/client_status.txt", "r")
    new_status = []
    for i, line in enumerate(client_status.read().splitlines()):
        if i == current_client:
            now = datetime.datetime.now()
            if now.hour < 15:
                # subtract 1 day
                now = now - datetime.timedelta(days = 1)
            new_status.append(now.strftime("%Y-%m-%d 15:00:00"))
        else:
            new_status.append(line)
    client_status.close()

    with open("client_secrets/client_status.txt", 'w') as client_status:
        for line in new_status:
            client_status.write(line + '\n')

def youtube_authentication(available_client):
    scopes = ["https://www.googleapis.com/auth/youtube.force-ssl"]

    # Disable OAuthlib's HTTPS verification when running locally.
    # *DO NOT* leave this option enabled in production.
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

    api_service_name = "youtube"
    api_version = "v3"
    client_secrets_file = f"client_secrets/CLIENT_SECRET{available_client}.json"

    # Get credentials and create an API client
    flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
        client_secrets_file, scopes)
    credentials = flow.run_local_server()
    youtube = googleapiclient.discovery.build(
        api_service_name, api_version, credentials=credentials)
    return youtube

def create_playlist(youtube, title):
    print(f'Creating "{title}".')
    request = youtube.playlists().insert(
        part="snippet,status",
        body={
          "snippet": {
            "title": title,
            "description": f"A playlist generated with Spotify2Youtube.",
            "defaultLanguage": "en"
          },
          "status": {
            "privacyStatus": "private"
          }
        }
    )
    created_playlist = request.execute()
    playlist_id = created_playlist["id"]
    username = created_playlist["snippet"]["channelTitle"]
    return playlist_id, username

def get_playlist_id(youtube, spotify_username, spotify_playlist):
    title = f"{spotify_playlist} - by {spotify_username}"
    request = youtube.playlists().list(
        part="snippet,contentDetails",
        maxResults=25,
        mine=True
    )
    response = request.execute()

    existing_playlists = response["items"]

    existing_titles = [playlist["snippet"]["title"] for playlist in existing_playlists]
    if title in existing_titles:
        playlist_id = existing_playlists[existing_titles.index(title)]["id"]
        username = existing_playlists[existing_titles.index(title)]["snippet"]["channelTitle"]
        print(f'"{title}" already exist.')
    else:
        playlist_id, username = create_playlist(youtube, title)
    return playlist_id, username

def get_max_viewcount_index(video_ids):
    request = youtube.videos().list(
        part="statistics",
        id = ",".join(video_ids)
    )
    response = request.execute()
    results = response["items"]
    view_counts = []
    for index, result in enumerate(results):
        try:
            view_counts.append(int(result["statistics"]["viewCount"]))
        except:
            print(f"https://www.youtube.com/watch?v={video_ids[index]}")
            pprint(result["statistics"])
            quit()
    return view_counts.index(max(view_counts))

def search(youtube, search_str):
    request = youtube.search().list(
        part="snippet",
        maxResults=5,
        q=search_str,
        type="video"
    )
    response = request.execute()

    results = response["items"]
    video_ids = []
    for result in results:
        video_ids.append(result["id"]["videoId"])
    max_viewcount_index = get_max_viewcount_index(video_ids)
    selected_result = results[max_viewcount_index]

    video_id = selected_result["id"]["videoId"]
    return video_id

def add_track(youtube, playlist_id, video_id):
    request = youtube.playlistItems().insert(
        part="snippet",
        body={
          "snippet": {
            "playlistId": playlist_id,
            "position": 0,
            "resourceId": {
              "kind": "youtube#video",
              "videoId": video_id
            }
          }
        }
    )
    response = request.execute()
    title = response["snippet"]["title"]
    playlistItemId = response["id"]
    return title, playlistItemId

def add_tracks(youtube, playlist_id, to_add, log_file):
    for index, row in to_add.iterrows():
        search_str = f"{row['Artist']} - {row['Track']}"
        video_id = search(youtube, search_str)
        title, playlistItemId = add_track(youtube, playlist_id, video_id)
        new_row = pd.DataFrame(row.append(pd.DataFrame([title,playlistItemId]))).T
        new_row.to_csv(log_file, mode='a', header=False,index=False)
        print(f"+ {title}")

def remove_tracks(youtube, to_del, old, log_file):
    for index, row in to_del.iterrows():
        request = youtube.playlistItems().delete(
            id = row["YT PlaylistItemId"]
        )
        response = request.execute()
        to_drop = old[ old['YT PlaylistItemId'] == row["YT PlaylistItemId"] ].index
        old.drop(to_drop , inplace=True)
        old.to_csv(log_file,index=False)
        print(f"- {row['YT Title']}")

if __name__ == "__main__":
    # get spotify tracks + artists + added times
    new, spotify_playlist, spotify_username = get_tracks()
    while True:
        print(f"""
Playlist information:
    Created by = {spotify_username}
    Title = {spotify_playlist}

Confirm conversion? [y/n]""")
        confirmation = str(input()).lower()
        if confirmation == "n":
            quit()
        elif confirmation == "y":
            break

    available_client = get_available_client()
    logging.getLogger('googleapiclient.discovery_cache').setLevel(logging.ERROR)
    logging.getLogger('googleapiclient.http').setLevel(logging.ERROR)
    try:
        # Youtube login
        youtube = youtube_authentication(available_client)

        # find/create youtube playlist
        playlist_id, youtube_username = get_playlist_id(youtube, spotify_username, spotify_playlist)
        log_file = f"history/{spotify_username}-{spotify_playlist}-{youtube_username}.csv"

        # find existing tracks
        try:
            old = pd.read_csv(log_file)
        except:
            old = pd.DataFrame(columns=["Spotify Id","Track","Artist","Added Date","YT Title", "YT PlaylistItemId"])
            old.to_csv(log_file,index=False)

        # compare with spotify tracks
        to_add = new[~new['Spotify Id'].isin(old['Spotify Id'])]
        to_del = old[~old['Spotify Id'].isin(new['Spotify Id'])]
        print(f"{len(to_del)} old tracks to delete.")
        print(f"{len(to_add)} new tracks to add.")
        print("==================================\n")

        # remove deleted tracks
        remove_tracks(youtube, to_del, old, log_file)

        # add new tracks
        add_tracks(youtube, playlist_id, to_add, log_file)

    except Exception as e:
        if not(str(e).startswith('<HttpError 403 when requesting ')&\
           (str(e).endswith(' returned "The request cannot be completed because you have exceeded your <a href="/youtube/v3/getting-started#quota">quota</a>.">')|
            (' returned "Daily Limit Exceeded. The quota will be reset at midnight Pacific Time (PT). You may monitor your quota usage and adjust limits in the API Console: ' in str(e)))):
            raise
        else:
            update_client_status(available_client)
            print("\n==================================\n")
            print(f"Quota for Client {available_client} is used up.")