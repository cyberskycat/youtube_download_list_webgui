import multiprocessing
import youtube_dl
from hashlib import sha1
from time import sleep

class MyLogger(object):
    def debug(self, msg):
        print(msg)
        # pass

    def warning(self, msg):
        print(msg)

    def error(self, msg):
        print(msg)

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
    "postprocessors":[{"key":"FFmpegEmbedSubtitle"}],
    "outtmpl":"./video_data/%(playlist_uploader)s-%(playlist_title)s/%(title)s-%(id)s.%(ext)s"
}

def url2tid(url):
    return sha1(url.encode()).hexdigest()



class downLoadWorker(multiprocessing.Process):
    def __init__(self,wid,url,app_store):
        super(downLoadWorker, self).__init__()
        self.wid = wid
        self.name = "download_worder_" + self.wid
        self.url = url
        self.app_store = app_store
    
    def run(self):
        print("worker:",self.wid)
        try:
            self.app_store.setFileData(self.wid,"status","downloading") 
            self.download()
            self.app_store.setFileData(self.wid,"status","finish") 
        except Exception:
            self.app_store.setFileData(self.wid,"status","error") 
        finally: 
            pass

    def download(self):
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            ydl.download([self.url])

    def stop(self):
        print('Terminating Process ... id',self.wid," start")
        #self.terminate()
        self.kill()
        self.join()
        print('Terminating Process ... id',self.wid," finish")
        self.app_store.setFileData(self.wid,"status","finish") 

        


class workerManager():
    worker_map = {}
    def __init__(self,worker_group_name,app_store):
        self.worker_group_name =worker_group_name
        self.app_store = app_store

    def get_all_worker(self):
        return self.worker_map

    def get_worker(self,wid):
        return self.worker_map[self.worker_group_name+"_"+wid]

    def add_to_worker_map(self,wid,worker):
        self.worker_map[self.worker_group_name+"_"+wid] = worker

    def clear_worker(self,wid):
        print("clear thread",self.worker_group_name+"_"+wid)
        del self.worker_map[self.worker_group_name+"_"+wid]

    def worker_is_runing(self,wid):
        return self.worker_group_name+"_"+wid  in self.worker_map

    def stop_worker(self,wid):
        if not self.worker_is_runing(wid):
            self.app_store.setFileData(wid,"status","finish") 
            return
            
        worker =self.worker_map[self.worker_group_name+"_"+wid]
        worker.stop()
        self.clear_worker(wid)
    
    def stop_all_worker(self):
        print("stop worker .............")
        for (k,worker) in self.worker_map.items():
            worker.stop()
        print("stop worker finish ...............")

    def start_worker(self,wid,url,app_store):
        if self.worker_is_runing(wid):
            return
        w = downLoadWorker(wid, url,app_store)
        w.start()
        self.add_to_worker_map(wid,w)