from __future__ import unicode_literals
import youtube_dl
import asyncio
from sanic import Sanic
from sanic.response import json
import pickle
import os
import threading
from hashlib import sha1
import time, threading
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


def download(url):
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])



#youtebe_list.pickledb
class Store:
    def __init__(self,dbname):
        if dbname is None or dbname == '':
            raise Exception("dbName is null")
        self.dbname = dbname
        #youtube data
        self.ydata={}
        self.shared_resource_lock = threading.Lock()
        self.get_store_data()

    def get_store_data(self):
        print(self.dbname)
        if os.path.isfile(self.dbname):
            with open(self.dbname,'rb') as f:
                data = pickle.load(f)
                self.ydata=data
        return self.ydata

    def save_store_data(self):
        self.shared_resource_lock.acquire()
        with open(self.dbname, 'wb') as f:
            pickle.dump(self.ydata, f, pickle.HIGHEST_PROTOCOL)
        self.shared_resource_lock.release()

    def get(self):
        return self.ydata

    def getElement(self,id):
        return self.ydata[id]

    def add(self,url):
        id=url2tid(url)
        if id in self.ydata:
            raise Exception("playlist already exists")
        self.ydata[id]={"id":id,"url":url,"lastSyncData":"","status":""}
        self.save_store_data()
        return id

    def remove(self,id):
        if id not in self.ydata:
            raise Exception("playlist not exists")
        del self.ydata[id]
        self.save_store_data()
        return id

    def setFileData(self,id,fieldName,filedValue):
        print("id:",id)
        if id in self.ydata:
            setdata = self.ydata[id]
            setdata[fieldName] = filedValue
            self.save_store_data()
        else:
            raise Exception("id not exists")

app = Sanic()
app_store = Store("youtebe.db")

# thread function
def download_thread_fun(id,url):
    app_store.setFileData(id,"status","downloading") 
    download(url)
    app_store.setFileData(id,"status","finish") 

#sync list info to db, if url is not a list ,will remove from db
def sync_list_info(id,url):
    list_info = extract_info(url)
    print('ssssssssssssssssssssssss',list_info)
    if list_info is None:
        app_store.remove(id)
        return
    
    if 'entries'  in  list_info and list_info["_type"] == "playlist":
        app_store.setFileData(id, "name", list_info["title"])
        app_store.setFileData(id, "uploader", list_info["uploader"])
        return
    else:
        app_store.remove(id)

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

@app.route('/addlist',methods=["GET",])
async def addlist(request):
    listurl = request.args["listurl"][0]
    if listurl is None or listurl.startswith("http://"):
            return json({"code":-1,"message":"list formt invaild"})
    listurl = listurl.strip() 
    try:
       id =  app_store.add(listurl)
       t = threading.Thread(target=sync_list_info,args=(id,listurl,), name='syncListInfoThread')
       t.start()
 
    except Exception:
        return json({"code":-1})
    return json({"code":1})

@app.route('/removelist',methods=["GET",])
async def removelist(request):
    id = request.args["id"][0]
    try:
       id =  app_store.remove(id)
    except Exception:
        return json({"code":-1})
    return json({"code":1})

@app.route('/syncList',methods=["GET",])
async def addlist(request):
    id = request.args["id"][0]
    # if app_store.getElement(id)["status"] == "downloading":
    #     return json({"code":-1,"message":"list is syncing"})

    if  app_store.getElement(id)["name"] is None :
        threading.Thread(target=sync_list_info,args=(id,url,), name='syncListInfoThread')
    url = app_store.getElement(id)["url"]
    # ydl_opts["outtmpl"]="./"+app_store.getElement(id)["name"]+"/%(title)s-%(id)s.%(ext)s"
    ydl_opts["outtmpl"]="./video_data/%(playlist_uploader)s-%(playlist_title)s/%(title)s-%(id)s.%(ext)s"
    try:
        
        t = threading.Thread(target=download_thread_fun,args=(id,url,), name='syncListThread')
        t.start()
        
    except Exception:
        return json({"code":-1})
    return json({"code":1})

@app.route('/status',methods=["GET",])
async def status(request):
    return json(app_store.get())

app.static('/static', './static')
app.static('/', './static/index.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5888)

# extract_info("https://www.youtube.com/playlist?list=PLt9WLG-do1avfIbJV1_Izpsv8sMH9-oBq")
