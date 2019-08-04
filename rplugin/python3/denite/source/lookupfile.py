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
        self.count=0
        self.redraw_done = True
        self.files = []
        self.caches = {}
        self.split = ';'
        self.vars = {
            'ignore': {
                'file': ['*.sw?','~$*','*.bak','*.exe','*.o','*.so','*.py[co]'],
                "dir" : [".git", ".svn", ".hg", "node_modules"]
            },
            'cache_dir': './',
        }

    def on_init(self, context):
        context['is_interactive'] = True
        context['is_async'] = False

    def get_cache_dir(self):
        cache_dir = self.vars['cache_dir']
        if not os.path.isdir(cache_dir):
            os.makedirs(cache_dir)
        return cache_dir

    def get_cache_path(self):
        cwd = os.getcwd()

        cwd = cwd.replace('/', '_')
        cwd = cwd.replace('\\', '_')
        cwd = cwd.replace(':', '_')

        cwd_dir = os.path.join(self.get_cache_dir(), cwd)
        if not os.path.isdir(cwd_dir):
            os.makedirs(cwd_dir)

        return os.path.join(cwd_dir, "filelist6")

    def gather_candidates(self, context):
        cache_path = self.get_cache_path()
        if not os.path.isfile(cache_path) or context["is_redraw"] == True:
            if not self.redraw_done:
                # self.vim.command('echo "please wait"')
                return []
            self.redraw_done = False
            ignore = self.vars['ignore']
            self.update_filelist(os.getcwd(), cache_path, ignore, "0")
            self.redraw_done = True
            context["is_redraw"] = False
            # self.vim.command('echo "Candidates redraw done!"')
        elif len(self.files) == 0:
            self.load_filelist(cache_path)

        return self.UnitePyGetResult(context["input"])

    def UnitePyGetResult(self, inputs):
        start_time = time.time()

        mrus = self.vim.call('denite#sources#lookupfile#mrus')
        self.mrus = [(os.path.basename(mru), os.path.dirname(mru)) for mru in mrus]

        rows_file = self.search(self.files, inputs, 20, True)
        rows_mru = self.search(self.mrus,  inputs, 20, False)

        lines = [{
            'word': ('%s%s%s' % (row[0], self.split, row[1])),
            'abbr': ('[M] %s' % get_path(row)),
            'kind': 'file',
            'group': 'file',
            'action__path': get_path(row),
            } for row in rows_mru]

        lines.extend([{
            'word': ('%s%s%s' % (row[0], self.split, row[1])),
            'abbr': ('[F] %s' % get_path(row)),
            'kind': 'file',
            'group': 'file',
            'action__path': get_path(row),
            } for row in rows_file if row not in rows_mru ])

        end_time = time.time()
        self.vim.command('echo "search %s cost %.1f ms, count:%d"' % (inputs, (end_time - start_time)*1000, len(lines)))

        return lines

    def search(self, rows, inputs, limit, is_cache):
        if inputs == "" or inputs == self.split:
            return rows if len(rows) <= limit else rows[:limit]

        rowsWithScore = []
        if is_cache and inputs in self.caches:
            rowsWithScore = self.caches[inputs]
        else:
            if is_cache and len(inputs) > 1:
                cacheInputs = inputs[:-1]
                if cacheInputs in self.caches:
                    rowsWithScore = self.caches[cacheInputs]
                    rows = [line for score, line in rowsWithScore]

            islower = is_search_lower(inputs)

            kwsAndDirs = inputs.split(self.split)
            inputs_file = (kwsAndDirs[0] if len(kwsAndDirs) > 0 else "").strip()
            inputs_dir  = (kwsAndDirs[1] if len(kwsAndDirs) > 1 else "").strip()

            progs = [(get_regex_prog(kw, islower), "name") for kw in inputs_file.split() if kw != ""]
            progs.extend([(get_regex_prog(kw, islower), "dir") for kw in inputs_dir.split() if kw != ""])

            rowsWithScore = self.do_search(rows, progs, islower)
            # save in cache
            if is_cache and len(progs) > 0:
                self.caches[inputs] = rowsWithScore

        return [line for score, line in heapq.nlargest(limit, rowsWithScore)]

    def do_search(self, rows, progs, islower):
        res = []

        for row in rows:
            filename = row[0].lower() if islower else row[0]
            dir = row[1].lower() if islower else row[1]
            scoreTotal = 0.0
            for (prog, tp) in progs:
                score = 0
                if tp == "name":
                    score = filename_score(prog, filename, dir)
                else:
                    score = dir_score(prog, dir)
                if score == 0:
                    scoreTotal = 0
                    break
                else:
                    scoreTotal += score

            if scoreTotal != 0:
                res.append((scoreTotal, row))

        return res

    def load_filelist(self, file_path):
        with open(file_path,'r') as f:
            lines = f.read().splitlines()
            self.files = []
            self.caches = {}
            for line in lines:
                items = line.split("\t")
                fileItem = (items[0], items[1])
                self.files.append(fileItem)
            f.close()

    def save_filelist(self, file_path, file_list):
        with open(file_path, 'w') as f:
            self.files = []
            self.caches = {}
            for item in file_list:
                try:
                    fileItem = (os.path.basename(item) , os.path.dirname(os.path.relpath(item)))
                    self.files.append(fileItem)
                    f.write("%s\t%s\n" % (fileItem))
                except UnicodeEncodeError:
                    continue

            f.close()

    def update_filelist(self, dir_path, file_path, wildignore, linksflag):
        start_time = time.time()
        file_list = []
        for dir_path, dirs, files in os.walk(dir_path, followlinks = False if linksflag == '0' else True):
            dirs[:] = [i for i in dirs if True not in (fnmatch.fnmatch(i,j)
                       for j in wildignore['dir'])]
            for name in files:
                if True not in (fnmatch.fnmatch(name, j) for j in wildignore['file']):
                    file_list.append(os.path.join(dir_path,name))
                if time.time() - start_time > 120:
                    self.save_filelist(file_path, file_list)
                    return

        self.save_filelist(file_path, file_list)

def filename_score(reprog, filename, dirname):
    result = reprog.search(filename)
    if result:
        score = result.start() * 2
        score = score + result.end() - result.start() + 1
        score = score + ( len(filename) + 1 ) / 100.0
        score = score + ( len(dirname) + 1 ) / 1000.0
        return 1000.0 / score

    return 0

def dir_score(reprog, line):
    result = reprog.search(line)
    if result:
        score = result.end() - result.start() + 1
        score = score + ( len(line) + 1 ) / 100.0
        return 1000.0 / score

    return 0

_escape = dict((c , "\\" + c) for c in ['^','$','.','{','}','(',')','[',']','\\','/','+'])
def get_regex_prog(kw, islower):
    searchkw = kw.lower() if islower else kw

    regex = ''
    # Escape all of the characters as necessary
    escaped = [_escape.get(c, c) for c in searchkw]

    if len(searchkw) > 1:
        regex = ''.join([c + "[^" + c + "]*" for c in escaped[:-1]])
    regex += escaped[-1]

    return re.compile(regex)

def contain_upper(kw):
    prog = re.compile('[A-Z]+')
    return prog.search(kw)

def is_search_lower(kw):
    return False if contain_upper(kw) else True

def get_path(row):
    return os.path.join(row[1], row[0])
