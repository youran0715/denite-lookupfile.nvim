#!/usr/bin/env python
# -*- coding: utf-8 -*-

import vim
import os

mrus = []

def add_mru(path):
    file_name = os.path.basename(path)
    dir_name = os.path.dirname(os.path.relpath(path))

    global mrus
    item = (file_name, dir_name)
    # print("item:%s" % str(item))
    try:
        mrus.remove(item)
    except Exception as e:
        pass
    # print("before")
    # print(mrus)
    mrus.insert(0, item)
    mrus = mrus if len(mrus) < 30 else mrus[0:30]
    # print("after")
    # print(mrus)

def UnitePyGetMrus():
    return mrus

def UnitePyAddMru():
    path = vim.eval('s:buf_path')
    if os.path.abspath(path).startswith(os.getcwd()):
        add_mru(path)

def UnitePyCleanMrus():
    global mrus
    mrus = []

def UnitePySaveMrus():
    file_path = vim.eval('s:file_path')
    with open(file_path, 'w') as f:
        global mrus
        for mru in mrus:
            # vim.command('echo "' + str(mru) + '"')
            try:
                f.write("%s\n" % (get_path(mru)))
            except UnicodeEncodeError:
                continue

        f.close()

def UnitePyLoadMrus():
    file_path = vim.eval('s:file_path')
    with open(file_path,'r') as f:
        lines = f.read().splitlines()
        global mrus
        mrus = []
        for line in lines:
            item = (os.path.basename(line), os.path.dirname(line))
            mrus.append(item)
        f.close()

