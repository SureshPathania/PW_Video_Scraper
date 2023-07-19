from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_cors import CORS, cross_origin
from googleapiclient.discovery import build
import requests
from bs4 import BeautifulSoup as bs
from urllib.request import urlopen as uReq
import logging
import re
import json
from config import api_key
logging.basicConfig(filename="video_scraper.log", level=logging.INFO)

#Function to retrieve Channel ID from Channel URL
def get_channel_id(url):
    html_page = bs(requests.get(url, cookies={"CONSENT" : "YES+1"}).text, "html.parser")
    data = re.search(r"var ytInitialData = ({.*});", str(html_page.prettify())).group(1)
    json_data = json.loads(data)
    channel_id = json_data["header"]["c4TabbedHeaderRenderer"]["channelId"]
    return channel_id

#Function to retrieve playlist of videos from the channel id 
def get_channel_playlist(youtube, channel_id):
    playlist_id = ""
    request = youtube.channels().list(part="snippet,contentDetails,statistics", id=channel_id)
    response = request.execute()
    for i in range(len(response['items'])):
        playlist_id = response['items'][i]['contentDetails']['relatedPlaylists']['uploads']
    return playlist_id

#Function to retrieve video ids from the playlist id
def get_video_ids(youtube, playlist_id):
    request = youtube.playlistItems().list(part='contentDetails', playlistId = playlist_id, maxResults = 50)
    response = request.execute()
    video_ids = []
    
    for i in range(len(response['items'])):
        video_ids.append(response['items'][i]['contentDetails']['videoId'])
        
    next_page_token = response.get('nextPageToken')
    more_pages = True
    
    while more_pages:
        if next_page_token is None:
            more_pages = False
        else:
            request = youtube.playlistItems().list(
                        part='contentDetails',
                        playlistId = playlist_id,
                        maxResults = 50,
                        pageToken = next_page_token)
            response = request.execute()
    
            for i in range(len(response['items'])):
                video_ids.append(response['items'][i]['contentDetails']['videoId'])
            
            next_page_token = response.get('nextPageToken')
        
    return video_ids

#Function to retrieve video ids of first 5 videos from the playlist id
def get_5_video_ids(youtube, playlist_id):
    request = youtube.playlistItems().list(part='contentDetails', playlistId = playlist_id, maxResults = 5)
    response = request.execute()
    video_ids = []
    for i in range(len(response['items'])):
        video_ids.append(response['items'][i]['contentDetails']['videoId'])    
    return video_ids

#Function to retrieve video details from the video ids
def get_video_details(youtube, video_ids):
    all_video_stats = []
    
    for i in range(0, len(video_ids), 50):
        request = youtube.videos().list(part='snippet,statistics', id=','.join(video_ids))
        response = request.execute()
        
        for video in response['items']:
            video_stats = dict(Video_URL = f"https://www.youtube.com/watch?v={video['id']}",
                               Thumbnail_URL = video["snippet"]["thumbnails"]["default"]["url"],
                               Title = video["snippet"]["title"],
                               Views = video["statistics"]["viewCount"],
                               Published_Date = video["snippet"]["publishedAt"],
                               )
            all_video_stats.append(video_stats)
    return all_video_stats

#Function to write scraped data in a .csv file
def write_data_in_file(search_string, mydict1):
    try:
        filename = search_string + ".csv"
        fw = open(filename, "w")
        headers = "Video_URL, Thumbnail_URL, Title, Views, Posting_Date \n"
        fw.write(headers)
        for i in mydict1:
            fw.write("{},{},{},{},{}\n".format(i["Video_URL"],i["Thumbnail_URL"],i["Title"],i["Views"],i["Published_Date"]))        
    except Exception as e:
        logging.error(e)
    fw.close()

#initializing flask app
app = Flask(__name__)                               

#setting up route for home page
@app.route("/", methods = ["POST","GET"])           
@cross_origin()
def home():
    return render_template("index.html")

#setting up route to process the form submitted in index.html
@app.route("/review", methods = ["POST", "GET"]) 
@cross_origin()
def review():
    if request.method == "POST":
        try:
            search_string = request.form["content"].replace(" ","")
            url = f"https://www.youtube.com/@{search_string}/videos"
            channel_id = get_channel_id(url)
            youtube = build("youtube","v3", developerKey = api_key)
            playlist = get_channel_playlist(youtube, channel_id)
            video_ids = get_5_video_ids(youtube,playlist)
            video_stats = get_video_details(youtube, video_ids)
            write_data_in_file(search_string, video_stats)

            return render_template("results.html", reviews=video_stats) 
        except Exception as e:
            logging.info(e)
            return "Oh!! Something went wrong."
    else:
        return render_template("index.html")

if __name__=="__main__":
    app.run(host="0.0.0.0", debug=True)