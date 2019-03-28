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
import atexit
import traceback
import multiprocessing
from video_type import VideoTypeEnum
import argparse

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
    with youtube_dl.YoutubeDL({}) as ydl:
        info_dict = ydl.extract_info(url, download=False,process=False)
        return info_dict

app = Sanic()
# app.config.KEEP_ALIVE = False
app_store = None  
app_store_single = None  
wmanager = None 
wmanager_single = None 

#sync list info to db, if url is not a list ,will remove from db
def sync_video_info(wid,url):
    list_info = extract_info(url)
    print("list_info",list_info)
    if list_info is None:
        app_store.remove(wid)
        return

    app_store.setFileData(wid, "name", list_info["title"])
    app_store.setFileData(wid, "uploader", list_info["uploader"]) 
    if 'entries'  in  list_info and list_info["_type"] == "playlist":
        app_store.setFileData(wid, "video_type","playlist" )  
        return
    else:
        app_store.setFileData(wid, "video_type","video" )  


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
    return json(app_store.get())


@app.route('/worker_lists',methods=["GET",])
async def  wlists(request):
    return json(wmanager.get_all_worker().keys())

@app.route('/addurl',methods=["GET",])
async def addlist(request):
    listurl = request.args["url"][0]
    if listurl is None or listurl.startswith("http://"):
            return json({"code":-1,"message":"list formt invaild"})
    listurl = listurl.strip() 
    try:
       wid =  app_store.add(listurl)
       t = threading.Thread(target=sync_video_info,args=(wid,listurl,), name='syncListInfoThread')
       t.start()
 
    except Exception:
        return json({"code":-1})
    return json({"code":1})

@app.route('/remove',methods=["GET",])
async def removelist(request):
    wid = request.args["wid"][0]
    try:
       wid =  app_store.remove(wid)
    except Exception:
        return json({"code":-1})
    return json({"code":1})

def parser_download_type(download_type_str):
    if download_type_str =="playlist":
        return VideoTypeEnum.LIST_VIDEO
    elif download_type_str == "video":
        return VideoTypeEnum.SINGLE_VIDEO
    else:
        raise Exception("error download type")

# download latest video ( list or single video) from the youtubelist
@app.route('/download',methods=["GET",])
async def download(request):
    print(request.args)
    wid = request.args["wid"][0]
    down_type = parser_download_type( request.args["down_type"][0])

    print("download id",wid)
    url = app_store.getElement(wid)["url"]
    try:
        wmanager.start_worker(wid,app_store,down_video_type=down_type)
        print("wid:",wid," start finish")

    except Exception :
        traceback.print_exc()
        return json({"code":-1})

    return json({"code":1})

@app.route('/stopDownload',methods=["GET",])
async def stopDownload(request):
    wid = request.args["wid"][0]
    if wid not in app_store.get():
        return json({"code":-1,"message":"id not exists"})
    wmanager.stop_worker(wid)
    return json({"code":1})

app.static('/static', './static')
app.static('/', './static/index.html')
app.static('/favicon.ico', './static/favicon.ico')

def parse_args():
    """
    :return:进行参数的解析
    """
    description = "download a youtube playlist  or single video"                   
    parser = argparse.ArgumentParser(description=description)       
    parser.add_argument('--datadir',help ="the directory store video data and app data ,default is app work dir", default="./")                  
    args = parser.parse_args()                                      
    if not args.datadir.startswith("/"):
        args.datadir = args.datadir+"/"
        
    return args

if __name__ == '__main__':
    config_args = parse_args()
    print("datadir=",config_args.datadir)
    multiprocessing.set_start_method('forkserver',force=True)
    multiprocessing.freeze_support()
    app_store = Store(config_args.datadir+"youtube.db")
    wmanager = workerManager("download__worker",app_store,video_store_dir=config_args.datadir)
    atexit.register(wmanager.stop_all_worker)
    app.run(host='0.0.0.0', port=5888,workers=1)
