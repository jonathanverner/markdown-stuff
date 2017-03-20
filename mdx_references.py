#! /usr/bin/env python


'''
Defs/Exs/Theorems Extension for Python-Markdown
===============================================

Adds support for definitions/theorems.


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


class ReferencesPattern(Pattern):

    def __init__(self):
        markdown.inlinepatterns.Pattern.__init__(self, r'{\s*ref:\s*#(?P<id>[^\s}]*)[\s]*}')

    def handleMatch(self, m):
        node = markdown.util.etree.Element('ref')
        node.set('key', markdown.util.AtomicString(m.group('id')))
        return node


class AnchorPattern(Pattern):
    def __init__(self):
        markdown.inlinepatterns.Pattern.__init__(self, r'{\s*\#(?P<id>[^\s}]*)\s*}')

    def handleMatch(self, m):
        node = markdown.util.etree.Element('label')
        node.set('key', markdown.util.AtomicString(m.group('id')))
        return node


class TOCNode(object):
    def __init__(self, title=None, root=False):
        self.title = title
        self.children = {}
        self.root = root

    def _get_child(self, id, create=True):
        if id in self.children:
            return self.children[id]
        if create:
            self.children[id] = TOCNode()
            return self.children[id]
        return None

    def _get_descendant(self, path, create=True):
        if len(path) == 0:
            return self
        child = self._get_child(path[0], create)
        if child:
            return child._get_descendant(path[1:], create)
        else:
            return child

    def to_element(self, prefix=''):
        if self.root:
            element = etree.Element('toc')
        else:
            element = etree.Element('li')
            if self.title:
                link = etree.SubElement(element, 'a')
                link.set('href', '#sec'+prefix)
                number = etree.SubElement(link, 'span')
                number.set('class', 'section_number')
                number.text = prefix
                title = etree.SubElement(link, 'span')
                title.text = self.title
            element.set('path', prefix)
        if len(prefix) > 0:
            prefix = prefix + '.'
        if len(self.children) > 0:
            children = etree.SubElement(element, 'ul')
            for (id, node) in sorted(self.children.items()):
                children.append(node.to_element(prefix+id))
        return element

    def insert_section(self, section_number, title):
        path = section_number.split('.')
        node = self._get_descendant(path, create=True)
        node.title = title


class BlockNumberingProcessor(Treeprocessor):
    def __init__(self, md_instance, number_referenced_only, number_by_type):
        self.depth_limit = 1
        self.current_section_tuple = [0]*self.depth_limit
        self.current_numbering = {}
        self.inBlock = False
        self.inBlockType = ''
        self.labels = {}
        self.number_by_type = number_by_type
        self.md = md_instance
        self.number_referenced_only = number_referenced_only

    def section(self, tag):
        depth = self._tag2depth(tag)
        if depth is None:
            return False
        logger.debug('SECTION: '+str(self.current_section_tuple)+'='+self.section_number())
        if depth < len(self.current_section_tuple):
            self.current_section_tuple[depth] += 1
            self.current_section_tuple = self.current_section_tuple[:depth+1]
        else:
            self.current_section_tuple.append(1)
        if depth < self.depth_limit:
            self.clear_numbering()
        return True

    def section_number(self, depth=None):
        if depth is None:
            depth = len(self.current_section_tuple)
        return '.'.join(map(lambda x: str(x), self.current_section_tuple[:depth]))

    def clear_numbering(self):
        for k in self.current_numbering:
            self.current_numbering[k] = 0

    def block_number(self, typ):
        if not self.number_by_type:
            typ = 'generic'
        logger.debug('BLOCK_NUMBER:'+str(self.current_numbering))
        return self.section_number(depth=self.depth_limit)+'.'+str(self.current_numbering[typ])

    def block_is_labeled(self, block):
        return block.find('.//label') is not None

    def next_number(self, typ):
        if not self.number_by_type:
            typ = 'generic'
        try:
            self.current_numbering[typ] += 1
        except:
            self.current_numbering[typ] = 1
        return self.block_number(typ)

    def _tag2depth(self, tag):
        if len(tag) != 2 or not tag.startswith('h'):
            return None
        try:
            return int(tag[1])-1
        except:
            return None

    def run(self, root):
        self.current_number = ''
        self._recursive_run(root)
        self._recursive_ref(root)
        return root

    def _recursive_ref(self, root):
        for child in root:
            logger.debug(child.tag)
            if child.tag == 'ref':
                    logger.debug(child.tag+'->'+child.get('key'))
                    number = etree.SubElement(child, 'a')
                    number.set('class', 'reference_number')
                    try:
                        number.text = self.labels[child.get('key', '')]
                        number.set('href', '#'+self.labels[child.get('key', '')])
                    except:
                        logger.warn('Undefined reference \''+child.get('key')+"'")
                        number.text = '??'
            else:
                    self._recursive_ref(child)

    def _recursive_run(self, root):
        clearInBlock = False
        for child in root:
            child_classes = child.get('class', '').split(' ')
            if self.section(child.tag):
                title = child.text
                child.text = ''
                number = etree.SubElement(child, 'span')
                number.set('id', 'sec'+self.section_number())
                number.set('class', 'section_number anchor')
                number.text = self.section_number()
                number.tail = title
                self.md.TOC.insert_section(self.section_number(), title)
            elif 'block' in child_classes:
                self.inBlock = True
                self.inBlockType = child.get('type', '')
                self.doNotNumber = True
                clearInBlock = True
                if 'do_not_number' not in child_classes:
                    if not self.number_referenced_only or self.block_is_labeled(child):
                        self.current_number = self.next_number(child.get('type', ''))
                        child.set('id', self.current_number)
                        child.set('class', child.get('class', '')+' anchor')
                        self.doNotNumber = False
                    else:
                        child.set('class', child.get('class', '')+' do_not_number')
            elif 'block_number' in child_classes:
                if not self.doNotNumber:
                    child.text = self.current_number
            elif 'label' == child.tag:
                if self.inBlock:
                    number = self.block_number(self.inBlockType)
                else:
                    number = 'sec'+self.section_number()
                self.labels[child.get('key', '')] = number
            self._recursive_run(child)
            if clearInBlock:
                self.inBlock = False


class ReferencesExtension(markdown.Extension):
    def __init__(self, configs):
        self.config['number_referenced_only'] = [False, False]
        self.config['number_by_type'] = [False, False]
        super(ReferencesExtension, self).__init__(configs)
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
        self.md.TOC = TOCNode(root=True)
        extNumbering = BlockNumberingProcessor(md, self.config.get('number_referenced_only', False), self.config.get('number_by_type', False))
        md.inlinePatterns.add('references', ReferencesPattern(), '_begin')
        md.inlinePatterns.add('anchors', AnchorPattern(), '_begin')
        md.treeprocessors.add('blocknumbering', extNumbering, '>inline')


def makeExtension(*args, **configs):
    if len(args) > 0 and isinstance(args[0], dict):
        return ReferencesExtension(configs=args[0])
    else:
        return ReferencesExtension(configs=configs)
