# coding: utf-8
# 【todo.txt .netの補助スクリプト】
#   todo.txtのrecursive task作成とarchiveをするスクリプト
#   rec:に対応していないのと、archiveがうまく動かないっぽいので。。。
from __future__ import print_function
import todotxt
import os

filename = u"C:\\Users\\localadmin\\Dropbox\\アプリ" \
           + u"\\Simpletask App Folder\\todo.txt"

archivef = u"C:\\Users\\localadmin\\Dropbox\\アプリ" \
           + u"\\Simpletask App Folder\\done.txt"

##filename = ("ttt.txt")

print("-- Input / Output Files")
tasks = todotxt.Tasks(filename, archivef)
print("todo.txt : [{0}]".format(os.path.abspath(tasks.path)))
print("done.txt : [{0}]".format(os.path.abspath(tasks.archive_path)))
print("\n-- Completed Recursive Task has no new Task create recursive" + \
      " and archive.")
tasks.load()
cnt = 0
for i in [x for x in tasks if x.recursive and x.finished]:
    if len([y for y in tasks if not y.finished and y.todo == i.todo]) == 0:
        print("[Wrn]:{0}".format(i.raw_todo))
        cnt += 1

modify_flag = False
if cnt > 0:
    ans = input("Create Recursive tasks?[y/N] :")
    if ans[0].lower() == "y":
        print("Create recursive tasks...")
        tasks.create_recursive_tasks()
        print("done..\n")
        modify_flag = True

else:
    print("There is no tasks need create recursive.\n")

if len([x for x in tasks if x.finished]) > 0:
    ans = input("Archive done tasks?[y/N] :")
    if ans[0].lower() == "y":
        print("Archive done.txt...")
        tasks.archive()
        print("done..\n")
        modify_flag = True

    else:
        print("Archive skipped...\n")
        tasks.archive_path = None


if modify_flag:
    ans = input("Save?[y/N] :")
    if ans[0].lower() == "y":
        print("Saving files...")
        tasks.save()
        print("done...\n")
    else:
        print("Saving skipped...\n")


print("\nToral Warning tasks: {0}".format(cnt))
print("Done.")
os.system("pause")
