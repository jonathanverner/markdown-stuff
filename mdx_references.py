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
try: from markdown import etree
except ImportError: from markdown.util import etree
import re
from markdown.treeprocessors import Treeprocessor
from markdown.inlinepatterns import Pattern

logger =  logging.getLogger(__name__)

class ReferencesPattern(Pattern):
  def __init__(self):
    markdown.inlinepatterns.Pattern.__init__(self, r'{\s*ref:\s*#(?P<id>[^\s}]*)[\s]*}')

  def handleMatch(self, m):
    node = markdown.util.etree.Element('ref')
    node.set('key',markdown.util.AtomicString(m.group('id')))
    return node



class BlockNumberingProcessor(Treeprocessor):
  def __init__(self,md_instance):
    self.depth_limit=1
    self.current_section_tuple = [0]*self.depth_limit
    self.current_numbering={}
    self.inBlock = False
    self.inBlockType = ''
    self.labels = {}
    self.number_by_type = False

  def section(self, tag):
    depth = self._tag2depth(tag)
    if depth is None:
      return False
    logger.debug('SECTION: '+str(self.current_section_tuple)+'='+self.section_number())
    if depth < len(self.current_section_tuple):
      self.current_section_tuple[depth]+=1
      self.current_section_tuple = self.current_section_tuple[:depth+1]
    else:
      self.current_section_tuple.append(1)
    if depth < self.depth_limit:
        self.clear_numbering()
    return True

  def section_number(self,depth=None):
    if depth is None:
      depth = len(self.current_section_tuple)
    return '.'.join(map(lambda x:str(x),self.current_section_tuple[:depth]))

  def clear_numbering(self):
      for k in self.current_numbering:
          self.current_numbering[k]=0

  def block_number(self,typ):
    if not self.number_by_type:
        typ = 'generic'
    logger.debug('BLOCK_NUMBER:'+str(self.current_numbering))
    return self.section_number(depth=self.depth_limit)+'.'+str(self.current_numbering[typ])

  def next_number(self, typ):
    if not self.number_by_type:
        typ = 'generic'
    try:
      self.current_numbering[typ] += 1
    except:
      self.current_numbering[typ] = 1
    return self.block_number(typ)

  def _tag2depth(self,tag):
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
        number = etree.SubElement(child,'span')
        logger.debug(child.tag+'->'+child.get('key'))
        number.set('class','reference_number')
        try:
          number.text = self.labels[child.get('key','')]
        except:
          number.text = '??'
      else:
        self._recursive_ref(child)



  def _recursive_run(self,root):
    clearInBlock = False
    for child in root:
      if self.section(child.tag):
        title = child.text
        child.text=''
        number = etree.SubElement(child,'span')
        number.set('class','section_number')
        number.text = self.section_number()
        number.tail=title
      elif 'block' in child.get('class','').split(' '):
        self.current_number = self.next_number(child.get('type',''))
        self.inBlock = True
        self.inBlockType = child.get('type','')
        clearInBlock = True
      elif 'block_number' in child.get('class','').split(' '):
        child.text = self.current_number
      elif 'label' == child.tag:
        if self.inBlock:
          number = self.block_number(self.inBlockType)
        else:
          number = self.section_number()
        self.labels[child.get('key','')] = number
      self._recursive_run(child)
      if clearInBlock:
        self.inBlock = False


class ReferencesExtension(markdown.Extension):
  def __init__(self,configs):
    pass

  def extendMarkdown(self,md,md_globals):
    self.md = md
    extNumbering = BlockNumberingProcessor(md)
    md.inlinePatterns.add('references', ReferencesPattern(), '_begin')
    md.treeprocessors.add('blocknumbering',extNumbering, '>inline')

def makeExtension(configs={}):
  return ReferencesExtension(configs=configs)
