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

import os
import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors

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
            new_status.append(now.strftime("%Y-%m-%d %H:%M:%S"))
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

    available_client = get_available_client()
    logging.getLogger('googleapiclient.discovery_cache').setLevel(logging.ERROR)
    logging.getLogger('googleapiclient.http').setLevel(logging.ERROR)
    try:
        # Youtube login
        youtube = youtube_authentication(available_client)

        # find/create youtube playlist
        log_file = f"history/callyong2005-cally-cally ong.csv"

        # find existing tracks
        old = pd.read_csv(log_file)

        # compare with spotify tracks
        to_del = old[old.duplicated("Spotify Id")]
        print(f"{len(to_del)} old tracks to delete.")
        pprint(to_del["Track"])
        print("==================================\n")

        # remove deleted tracks
        remove_tracks(youtube, to_del, old, log_file)


    except Exception as e:
        if not(str(e).startswith('<HttpError 403 when requesting ')&\
           (str(e).endswith(' returned "The request cannot be completed because you have exceeded your <a href="/youtube/v3/getting-started#quota">quota</a>.">')|
            (' returned "Daily Limit Exceeded. The quota will be reset at midnight Pacific Time (PT). You may monitor your quota usage and adjust limits in the API Console: ' in str(e)))):
            print(f'ERROR  :    {type(e).__name__}')
            print(f'MESSAGE:    {e}')
        else:
            update_client_status(available_client)
            print("\n==================================\n")
            print(f"Quota for Client {available_client} is used up.")