# coding: utf-8
import todotxt
import os

filename = u"C:\\Users\\localadmin\\Dropbox\\アプリ" \
           + u"\\Simpletask App Folder\\todo.txt"
##filename = ("ttt.txt")
print("-- Completed Recursive Task has no new Task --")
tasks = todotxt.Tasks(filename)
print("[{0}]".format(os.path.abspath(tasks.path)))
tasks.load()
cnt = 0
for i in [x for x in tasks if x.recursive and x.finished]:
    if len([y for y in tasks if not y.finished and y.todo == i.todo]) == 0:
        print("[Wrn]:{0}".format(i.raw_todo))
        cnt += 1
print("\nToral Warning tasks: {0}".format(cnt))
print("Done.")
os.system("pause")
