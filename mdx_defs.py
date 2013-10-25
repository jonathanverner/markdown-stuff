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
from markdown.blockprocessors import BlockProcessor

logger =  logging.getLogger(__name__)

def build_headings_css(doc, position='before'):

    def walk(node):
        ret = set([])
        for child in node:
            if 'block' in child.get('class','').split(' '):
                ret.add(child.get('type',''))
            ret = ret.union(walk(child))
        return ret

    block_types = walk(doc)
    css = ''
    if position == 'after':
        space_after=' '
    else:
        space_after=''
    for bt in block_types:
        css += '.block_heading[type="'+bt+'"]:'+position+" {\n  content:'"+bt+space_after+"'\n}\n"
    return css

class DefinitionBlockProcessor(BlockProcessor):

  START_RE = re.compile(r"""
      ^\s*                            # A definition block starts with possible whitespace,
      (?:{\s*\#(?P<id>[^\s}]*)\s*})*  # followed by an optional #id in curly braces,
      \s*
      (?P<type>[^\s:]*)               # then comes the block type (e.g. theorem, example, etc.),
      \s*
      (?:\((?P<name>[^)]*)\))*        # optional name in parenthesis,
      \s*
      (?:\[(?P<references>[^\]]*)\])* # optional references come in square brackegs (e.g. [ Balcar, Dow ]),
      \s*
      :                               # and finally a colon
      \s*                             # some whitespace (which will be discarded)
      (?P<rest>.*)                    # and the rest of the block
  """, re.VERBOSE | re.DOTALL)

  END_RE = re.compile(r'(.*){}\s*$', re.DOTALL)

  BLOCKTYPES = ['Theorem','Proposition','Lemma','Fact','Observation','Definition','Example','Remark']


  def test(self, parent, block):
    match = self.START_RE.match(block)
    if match and match.group('type') in self.BLOCKTYPES:
      # Disallow nested definition blocks
      if self.parser.state.isstate('definition_block'):
        logger.warn("Nested definition blocks not allowed: %r" % block)
        return False
      return True
    return False

  def add_info(self, element, match):
    element.set('class','block '+match['type'])
    element.set('type',match['type'])
    if match['id']:
      element.set('id',match['id'])
      label=etree.SubElement(element,'label')
      label.set('key',match['id'])
    heading = etree.SubElement(element,'span')
    heading.set('class','block_heading')
    heading.set('type',match['type'])
    number = etree.SubElement(heading,'span')
    number.set('class','block_number')

    if match['name']:
      element.set('name',match['name'])
      name_heading = etree.SubElement(element,'span')
      name_heading.set('class','block_name')
      name_heading.text = match['name']

    if match['references']:
      element.set('references',match['references'])
      ref_heading = etree.SubElement(element,'span')
      ref_heading.set('class','block_references')
      ref_heading.text = match['references']

  def run(self, parent, blocks):
    block = blocks.pop(0)
    m = self.START_RE.match(block).groupdict()
    def_element = etree.SubElement(parent, 'div')
    self.add_info(def_element,m)
    self.parser.state.set('definition_block')
    block_text = m['rest']
    m = self.END_RE.match(block_text)
    if m:
      block_text = m.group(1)
      end_block = True
    else:
      end_block = False
    while not end_block:
      self.parser.parseBlocks(def_element,[block_text])
      block_text = blocks.pop(0)
      m = self.END_RE.match(block_text)
      if m:
        block_text = m.group(1)
        end_block = True
      if len(blocks) == 0:
        break;
    if not end_block:
      logger.warn("Unterminated definition block: %r" % block)
    self.parser.parseBlocks(def_element,[block_text])
    self.parser.state.reset()


class DefinitionBlockExtension(markdown.Extension):
  def __init__(self,configs):
    pass

  def extendMarkdown(self,md,md_globals):
    self.md = md
    ext = DefinitionBlockProcessor(md.parser)
    md.parser.blockprocessors.add('definitionblock',ext, '_begin')

def makeExtension(configs={}):
  return DefinitionBlockExtension(configs=configs)
