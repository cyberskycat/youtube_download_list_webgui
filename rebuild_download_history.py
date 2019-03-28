from os import walk
f = []
mypath="./"
file_extend=("mkv","webm","mp4")
for (dirpath, dirnames, filenames) in walk(mypath):
    f.extend(filenames)
wfile=open("download_history.txt","w")
for i in f:
    if i.endswith("mkv") or i.endswith("mp4") or  i.endswith("webm"):
        split_data = i.split(".")
        #print(split_data[-2])
        id= split_data[-2][-11:]
        print(id)
        wfile.write("youtube "+id+"\n")
        
wfile.close()
