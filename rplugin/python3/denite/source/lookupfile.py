#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Distributed under terms of the MIT license.

from .base import Base
import denite.util
import subprocess
import tempfile
import re
import time
import os
import heapq
import platform
import fnmatch

class Source(Base):
    def __init__(self, vim):
        super().__init__(vim)
        self.name = 'lookupfile'
        self.kind = 'file'
        self.persist_actions = []
        self.files = []
        self.key_files = 'lookupfiles'
        self.key_mrus = 'lookupmrus'
        self.key_edit = 'lookupeidt'
        self.vars = {
            'ignore': {
                'file': ['*.sw?','~$*','*.bak','*.exe','*.o','*.so','*.py[co]'],
                "dir" : [".git", ".svn", ".hg", "node_modules"]
            }
        }

    def on_init(self, context):
        context['is_interactive'] = True

    def get_cache_dir(self):
        cache_dir = os.getenv("HOME") + "/.cache/vim/"
        if not os.path.isdir(cache_dir):
            os.makedirs(cache_dir)
        return cache_dir

    def get_cache_path(self):
        cwd = os.getcwd()

        cwd = cwd.replace('/', '_')
        cwd = cwd.replace(':', '_')

        return os.path.join(self.get_cache_dir(), cwd, "filelist2")

    def map_result(self, rows, prefix):
        return [{
            'word': x,
            'abbr': prefix + x,
            'action__path': x,
            } for x in rows]

    def gather_candidates(self, context):
        cache_path = self.get_cache_path()
        if not os.path.isfile(cache_path) or context["is_redraw"] == True:
            ignore = self.vars['ignore']
            self.files = UpdateFileList(os.getcwd(), cache_path, ignore, "0")
            SetCandidates(self.key_files, self.files)
        elif len(self.files) == 0:
            self.files = LoadCandidates(self.key_files, cache_path)

        input = context["input"]

        if input == "":
            cwd = os.getcwd()
            mrus = self.vim.call('neomru#_gather_file_candidates')
            # 转为相对路径
            mrus = [os.path.relpath(x) for x in mrus if x.startswith(cwd)]
            SetCandidates(self.key_mrus, mrus)

        rowsM = uniteMatch(self.key_mrus, context["input"], 20, "filename-only")
        # rows2 = uniteMatch(self.key_files, context["input"], 20, "filename-only")
        rowsF = uniteMatch(self.key_files, context["input"], 20, "filename-only")

        # 去掉在MRU中已有的
        rowsF2 = []
        for f in rowsF:
            exist = False
            for m in rowsM:
                if m == f:
                    exist = True
            if not exist:
                rowsF2.append(f)


        resM = self.map_result(rowsM,  '[M] ')
        resF = self.map_result(rowsF2, '[F] ')

        resM.extend(resF)
        return resM

def saveFileList(file_path, file_list):
    with open(file_path, 'w') as f:
        for item in file_list:
            try:
                f.write("%s\n" % os.path.relpath(item))
            except UnicodeEncodeError:
                continue

        f.close()

def UpdateFileList(dir_path, file_path, wildignore, linksflag):
    start_time = time.time()
    file_list = []
    for dir_path, dirs, files in os.walk(dir_path, followlinks = False
            if linksflag == '0' else True):
        dirs[:] = [i for i in dirs if True not in (fnmatch.fnmatch(i,j)
                   for j in wildignore['dir'])]
        for name in files:
            if True not in (fnmatch.fnmatch(name, j)
                            for j in wildignore['file']):
                file_list.append(os.path.join(dir_path,name))
            if time.time() - start_time > 120:
                writelist2file(file_path, file_list)
                return

    saveFileList(file_path, file_list)
    return file_list


_escape = dict((c , "\\" + c) for c in ['^','$','.','{','}','(',')','[',']','\\','/','+'])

def filename_score(reprog, path, slash):
    # get filename via reverse find to improve performance
    slashPos = path.rfind(slash)
    filename = path[slashPos + 1:] if slashPos != -1 else path

    result = reprog.search(filename)
    if result:
        score = result.start() * 2
        score = score + result.end() - result.start() + 1
        score = score + ( len(filename) + 1 ) / 100.0
        score = score + ( len(path) + 1 ) / 1000.0
        return 1000.0 / score

    return 0

def path_score(reprog, line):
    result = reprog.search(line)
    if result:
        score = result.end() - result.start() + 1
        score = score + ( len(line) + 1 ) / 100.0
        return 1000.0 / score

    return 0

def dir_score(reprog, line):
    result = reprog.search(os.path.dirname(line))
    if result:
        score = result.end() - result.start() + 1
        score = score + ( len(line) + 1 ) / 100.0
        return 1000.0 / score

    return 0

def contain_upper(kw):
    prog = re.compile('[A-Z]+')
    return prog.search(kw)

def is_search_lower(kw):
    return False if contain_upper(kw) else True

def get_regex_prog(kw, isregex, islower):
    searchkw = kw.lower() if islower else kw

    regex = ''
    # Escape all of the characters as necessary
    escaped = [_escape.get(c, c) for c in searchkw]

    if isregex:
        if len(searchkw) > 1:
            regex = ''.join([c + "[^" + c + "]*" for c in escaped[:-1]])
        regex += escaped[-1]
    else:
        regex = ''.join(escaped)

    return re.compile(regex)

def Match(opts, rows, islower):
    res = []

    slash = '/' if platform.system() != "Windows" else '\\'

    for row in rows:
        line = row.lower() if islower else row
        scoreTotal = 0.0
        for kw, prog, mode in opts:
            score = 0.0

            if mode == 'filename-only':
                score = filename_score(prog, line, slash)
            elif mode == 'dir':
                score = dir_score(prog, line)
            else:
                score = path_score(prog, line)

            if score == 0:
                scoreTotal = 0
                break
            else:
                scoreTotal+=score

        if scoreTotal != 0:
            res.append((scoreTotal, row))

    return res

def GetFilterRows(rowsWithScore):
    rez = []
    rez.extend([line for score, line in rowsWithScore])
    return rez

def Sort(rowsWithScore, limit):
    rez = []
    rez.extend([line for score, line in heapq.nlargest(limit, rowsWithScore) if score != 0])
    return rez

candidates = {}
def SetCandidates(key, items):
    candidates[key] = items
    clearCache(key)

def LoadCandidates(key, path):
    items = []
    with open(path,'r') as f:
        items = f.read().splitlines()

    SetCandidates(key, items)
    return items

candidatesCache = {}
resultCache = {}
def clearCache(key):
    candidatesCache[key] = {}
    resultCache[key] = {}

def getCacheKey(key, inputs):
    return key + "@" + inputs

def setCandidatesToCache(key, inputs, items):
    cache = candidatesCache.get(key, {})
    cache[inputs] = items

def getCandidatesFromCache(key, inputs):
    cache = candidatesCache.get(key, {})
    return cache.get(inputs, [])

def setResultToCache(key, inputs, items):
    cache = resultCache.get(key, {})
    cache[inputs] = items

def getResultFromCache(key, inputs):
    cache = resultCache.get(key, {})
    return cache.get(inputs, [])

def existCache(key, inputs):
    if key not in resultCache:
        return False

    if inputs not in resultCache[key]:
        return False

    return True

def getCandidates(key, inputs):
    if len(inputs) <= 1:
        return candidates.get(key, [])

    cacheInputs = inputs[:-1]
    if existCache(key, cacheInputs):
        return getCandidatesFromCache(key, cacheInputs)

    return candidates.get(key, [])

def uniteMatch(key, inputs, limit, mmode):
    isregex = True
    smartcase = True

    if existCache(key, inputs):
        return getResultFromCache(key, inputs)

    items = getCandidates(key, inputs)

    rows = items
    rowsFilter = items

    kwsAndDirs = inputs.split(';')
    strKws = kwsAndDirs[0] if len(kwsAndDirs) > 0 else ""
    strDir = kwsAndDirs[1] if len(kwsAndDirs) > 1 else ""

    islower = is_search_lower(inputs)

    opts = [(kw, get_regex_prog(kw, isregex, islower), mmode) for kw in strKws.split() if kw != ""]

    if strDir != "":
        opts.append((strDir, get_regex_prog(strDir, isregex, islower), 'dir'))

    if len(opts) > 0:
        rowsWithScore = Match(opts, rows, islower)
        rowsFilter = GetFilterRows(rowsWithScore)
        rows = Sort(rowsWithScore, limit)

        setCandidatesToCache(key, inputs, rowsFilter)
        setResultToCache(key, inputs, rows)

    if len(rows) > limit:
        rows = rows[:limit]

    return rows

def ClearCache(key):
    clearCache(key)
