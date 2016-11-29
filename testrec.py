# coding: utf-8
import todotxt
import os

filename = u"C:\\Users\\localadmin\\Dropbox\\アプリ" \
           + u"\\Simpletask App Folder\\todo.txt"
##filename = ("ttt.txt")
tasks = todotxt.Tasks(filename)
tasks.load()
cnt = 0
for i in [x for x in tasks if x.recursive and x.finished]:
    print i
    if len([y for y in tasks if not y.finished and y.todo == i.todo]) == 0:
        print("[Wrn]:{0}".format(x.raw_todo))
        cnt += 1
print("\nToral Warning Count: {0}".format(cnt))
os.system("pause")
