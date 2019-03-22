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
    "postprocessors":[{"key":"FFmpegEmbedSubtitle"}]
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
        self.logger.info('Terminating Process ...')
        self.terminate()
        self.join()

def start_worker(wid,url,app_store):
    w = downLoadWorker(wid, url,app_store)
    w.start()
