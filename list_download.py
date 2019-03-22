from __future__ import unicode_literals
import youtube_dl
import asyncio
from sanic import Sanic
from sanic.response import json
import pickle
import os
import threading
from  store import Store
from hashlib import sha1
import time, threading
from worker import *
class MyLogger(object):
    def debug(self, msg):
        print(msg)
        # pass

    def warning(self, msg):
        print(msg)

    def error(self, msg):
        print(msg)

def url2tid(url):
    return sha1(url.encode()).hexdigest()

def my_hook(d):
    # print(d)
    if d['status'] == 'finished':
        print(d['filename'])


ydl_opts = {
    # 'format':'worstaudio',
    'yesplaylist': 'true',
    'logger': MyLogger(),
    'progress_hooks': [my_hook],
    'download_archive':"./download_history.txt",
    'ignoreerrors':'true',
    'writesubtitles':'true',
    'writeautomaticsub':'true',
    'subtitleslangs':['en','zh-Hans','zh-Hant'],
    "postprocessors":[{"key":"FFmpegEmbedSubtitle"}]
}
def getPlayList(listUrl):
    video_url_list = []
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        print("listUrl:",listUrl)
        info_dict = ydl.extract_info(listUrl, download=False,process=False)
        print(info_dict)
        if 'entries' not in info_dict:
            return video_url_list
        for video in info_dict['entries']:
            if not video:
                print('ERROR: Unable to get info. Continuing...')
                continue
            video_url_list.append({"id":video.get("id"),"title":video.get("title")})
    return video_url_list

def extract_info(url):
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(url, download=False,process=False)
        return info_dict

app = Sanic()
app_store = Store("youtebe.db")
#store runing thread
thread_map = {}

def add_to_thread_map(thread_group_name,id,thread_entity):
    thread_map[thread_group_name+"_"+id] = thread_entity

def clear_thread(thread_group_name,id):
    print("clear thread",thread_group_name+"_"+id)
    del thread_map[thread_group_name+"_"+id]

def thread_is_woring(thread_group_name,id):
    return thread_group_name+"_"+id  in thread_map

def stop_thread(thread_group_name,id):
    t = thread_map[thread_group_name+"_"+id]
    t._stop()


#sync list info to db, if url is not a list ,will remove from db
def sync_list_info(wid,url):
    list_info = extract_info(url)
    print("list_info",list_info)
    if list_info is None:
        app_store.remove(wid)
        return
    
    if 'entries'  in  list_info and list_info["_type"] == "playlist":
        app_store.setFileData(wid, "name", list_info["title"])
        app_store.setFileData(wid, "uploader", list_info["uploader"])
        return
    else:
        app_store.remove(wid)


# get all video list from a list or channel
@app.route('/videooflist',methods=["GET",])
async def videooflist(request):
    # print("request:",request.args)
    listurl = request.args["listurl"][0]
    data = getPlayList(listurl)
    print(data)
    return json(data)

@app.route('/lists',methods=["GET",])
async def  lists(request):
    print(thread_map)
    return json(app_store.get())

@app.route('/addlist',methods=["GET",])
async def addlist(request):
    listurl = request.args["listurl"][0]
    if listurl is None or listurl.startswith("http://"):
            return json({"code":-1,"message":"list formt invaild"})
    listurl = listurl.strip() 
    try:
       wid =  app_store.add(listurl)
       t = threading.Thread(target=sync_list_info,args=(wid,listurl,), name='syncListInfoThread')
       t.start()
 
    except Exception:
        return json({"code":-1})
    return json({"code":1})

@app.route('/removelist',methods=["GET",])
async def removelist(request):
    wid = request.args["wid"][0]
    try:
       wid =  app_store.remove(wid)
    except Exception:
        return json({"code":-1})
    return json({"code":1})

# download latest video from the youtubelist
@app.route('/syncList',methods=["GET",])
async def syncList(request):
    print(request.args)
    wid = request.args["wid"][0]
    print("syncList id",wid)
    # if thread_is_woring("syncListThread",id):
    #     return json({"code":-1,"message":"list is syncing"})

    if  app_store.getElement(wid)["name"] is None :
        threading.Thread(target=sync_list_info,args=(wid,url,), name='syncListInfoThread')
    url = app_store.getElement(wid)["url"]
    ydl_opts["outtmpl"]="./video_data/%(playlist_uploader)s-%(playlist_title)s/%(title)s-%(id)s.%(ext)s"
    try:
        # t = threading.Thread(target=download_thread_fun,args=(id,url), kwargs={"call_back_function":clear_thread}, name='syncListThread')
        # add_to_thread_map("syncListThread",id,t) 
        # t.start()
        start_worker(wid,url,app_store)
    except Exception:
        return json({"code":-1})
    return json({"code":1})

@app.route('/stopSyncList',methods=["GET",])
async def status(request):
    wid = request.args["wid"][0]
    if wid not in app_store.get():
        return json({"code":-1,"message":"id not exists"})

    if thread_is_woring("syncListThread",id):
        pass
    else:
        return json({"code":-1,"message":"task not start"})
    return json(app_store.get())

app.static('/static', './static')
app.static('/', './static/index.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5888)

# extract_info("https://www.youtube.com/playlist?list=PLt9WLG-do1avfIbJV1_Izpsv8sMH9-oBq")
