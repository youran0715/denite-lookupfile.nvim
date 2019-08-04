#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re

from denite.base.filter import Base
from denite.util import convert2fuzzy_pattern

def escape_fuzzy(string):
    # Escape string for python regexp.
    p = re.sub(r'([;a-zA-Z0-9_-])(?!$)', r'\1[^\1]*', string)
    p = re.sub(r'/(?!$)', r'/[^/]*', p)
    return p

class Filter(Base):

    def __init__(self, vim):
        super().__init__(vim)

        self.name = 'matcher/exfuzzy'
        self.description = 'my fuzzy matcher'

    def filter(self, context):
        if context['input'] == '':
            return context['candidates']
        pattern = context['input']
        if context['ignorecase']:
            pattern = pattern.lower()
        p = re.compile(escape_fuzzy(re.escape(pattern)))
        if context['ignorecase']:
            context['candidates'] = [x for x in context['candidates']
                                     if p.search(x['word'].lower())]
        else:
            context['candidates'] = [x for x in context['candidates']
                                     if p.search(x['word'])]
        return context['candidates']

    def convert_pattern(self, input_str):
        return convert2fuzzy_pattern(input_str)
