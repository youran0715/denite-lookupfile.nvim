#!/usr/bin/env python
# -*- coding: utf-8 -*-

import vim
import os

mrus = []

def add_mru(path):
    relpath = os.path.relpath(path)

    global mrus
    try:
        mrus.remove(relpath)
    except Exception as e:
        pass
    mrus.insert(0, relpath)
    mrus = mrus if len(mrus) < 30 else mrus[0:30]
    # print("after")
    # print(mrus)

def UnitePyGetMrus():
    global mrus
    vim.command('let s:mrus = %s' % str(mrus))

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
                f.write("%s\n" % mru)
            except UnicodeEncodeError:
                continue

        f.close()

def UnitePyLoadMrus():
    file_path = vim.eval('s:file_path')
    with open(file_path,'r') as f:
        global mrus
        mrus = f.read().splitlines()
        f.close()

