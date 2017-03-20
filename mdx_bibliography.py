#! /usr/bin/env python


'''
Bibliography Extension for Python-Markdown
===============================================

Adds support for bibliography.


Usage
-----

'''

import logging
import markdown
try:
    from markdown import etree
except ImportError:
    from markdown.util import etree
from markdown.treeprocessors import Treeprocessor
from markdown.inlinepatterns import Pattern
import re


logger = logging.getLogger(__name__)


class BibliographyPattern(Pattern):
    def __init__(self):
        markdown.inlinepatterns.Pattern.__init__(self, r'{\s*bib:\s*(?P<id>[^\s}]*)[\s]*}')

    def handleMatch(self, m):
        node = markdown.util.etree.Element('bib')
        node.set('key', markdown.util.AtomicString(m.group('id')))
        return node


class BibliographyExtension(markdown.Extension):
    def __init__(self, configs):
        super(BibliographyExtension, self).__init__(configs)
        cfg = {}
        try:
            for (key, val) in self.config:
                cfg[key] = val
        except:
            for (key, val) in self.config.items():
                cfg[key] = val[0]
        self.config = cfg

    def extendMarkdown(self, md, md_globals):
        self.md = md
        md.inlinePatterns.add('bibreferences', BibliographyPattern(), '_begin')


def makeExtension(*args, **configs):
    if len(args) > 0 and isinstance(args[0], dict):
        return BibliographyExtension(configs=args[0])
    else:
        return BibliographyExtension(configs=configs)
