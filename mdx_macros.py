#! /usr/bin/env python


'''
Macros Extension for Python-Markdown
===============================================

Adds support for macros.


Usage
-----

'''

import logging
import markdown
try: from markdown import etree
except ImportError: from markdown.util import etree
import re
from markdown.treeprocessors import Treeprocessor
from markdown.inlinepatterns import Pattern

logger =  logging.getLogger(__name__)

class MacroDefPattern(Pattern):
    def __init__(self):
        markdown.inlinepatterns.Pattern.__init__(self, r'\s*@(?P<name>\w*)\s*(\((?P<args>[^)]*)\))?\s*:=\s*(?P<body>[^\n]*)')
        self.macros={}

    def handleMatch(self, m):
        md = m.groupdict()
        node = markdown.util.etree.Element('macro')
        node.set('name',md['name'])
        if md['args']:
            node.set('args',md['args'])
        node.set('body',md['body'])
        md = m.groupdict()
        self.macros[md['name']]=md
        return node

class MacroPattern(Pattern):
    def __init__(self,definitions):
        self.defs = definitions
        markdown.inlinepatterns.Pattern.__init__(self,r'(?P<all>@(?P<name>\w*)(\((?P<args>[^)]*)\))?)')

    def handleMatch(self,m):
        md = m.groupdict()
        if not md['name'] in self.defs.macros:
            return md['all']
        macro = self.defs.macros[md['name']]
        ret = macro['body']
        if macro['args']:
            if not md['args']:
                return md['all']
            else:
                arg_vals = md['args'].split(',')
                arg_names = macro['args'].split(',')
                if len(arg_vals) != len(arg_names):
                    return md['all']
                for i in range(len(arg_vals)):
                    ret = ret.replace(arg_names[i],arg_vals[i])
        return ret

class MacrosExtension(markdown.Extension):
  def __init__(self,configs):
    pass

  def extendMarkdown(self,md,md_globals):
    self.md = md
    self.mdefPAT = MacroDefPattern()
    self.macroPAT = MacroPattern(self.mdefPAT)
    md.inlinePatterns.add('macrodef', self.mdefPAT, '_begin')
    md.inlinePatterns.add('macro', self.macroPAT, '>macrodef')

def makeExtension(configs={}):
  return MacrosExtension(configs=configs)
