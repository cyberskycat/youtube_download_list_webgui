import multiprocessing
import pickle
import os
from hashlib import sha1
def url2tid(url):
    return sha1(url.encode()).hexdigest()
class Store:
    def __init__(self,dbname):
        if dbname is None or dbname == '':
            raise Exception("dbName is null")
        self.dbname = dbname
        #youtube data
        with multiprocessing.Manager() as MG:
                    self.ydata=multiprocessing.Manager().dict()
        self.shared_resource_lock = multiprocessing.Lock() 
        self.get_store_data()

    def get_store_data(self):
        print(self.dbname)
        if os.path.isfile(self.dbname):
            with open(self.dbname,'rb') as f:
                data = pickle.load(f)
                with multiprocessing.Manager() as MG:
                    self.ydata=multiprocessing.Manager().dict(data)
        return self.ydata

    def save_store_data(self):
        self.shared_resource_lock.acquire()
        with open(self.dbname, 'wb') as f:
            pickle.dump(dict(self.ydata), f, pickle.HIGHEST_PROTOCOL)
        self.shared_resource_lock.release()

    def get(self):
        return dict(self.ydata)

    def getElement(self,wid):
        return self.ydata[wid]

    def add(self,url):
        wid=url2tid(url)
        if wid in self.ydata:
            raise Exception("playlist already exists")
        self.ydata[wid]={"wid":wid,"url":url,"lastSyncData":"","status":""}
        print(dict(self.ydata))
        self.save_store_data()
        return wid

    def remove(self,wid):
        if wid not in self.ydata:
            raise Exception("playlist not exists")
        del self.ydata[wid]
        self.save_store_data()

    def setFileData(self,wid,fieldName,filedValue):
        print("wid:"+wid)
        if wid in self.ydata:
            ldata = self.ydata[wid]
            ldata[fieldName] = filedValue
            self.ydata[wid] = ldata
            self.save_store_data()
        else:
            raise Exception("id not exists")