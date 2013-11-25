#! /usr/bin/env python
# -*- coding:utf-8 -*-

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

def _css_from_blocktypes(types, position):
    css = u"""
.qed:after {
  content:'□';
  font-size:1.5em;
}

.qed {
  float:right;
  text-align:right;
  margin-top:-0.3em;
}
"""
    if position == 'after':
        space_after=' '
    else:
        space_after=''
    for bt in types:
        css += '.block_heading[type="'+bt+'"]:'+position+" {\n  content:'"+bt+space_after+"'\n}\n"
    return css

def _latex_from_blocktypes(types,position):
    if position == 'after':
        ret = u'\\swapnumbers\n'
    else:
        ret = u''
    for bt in types:
        if bt not in DefinitionBlockProcessor.PROOFS:
            ret += u'\\newtheorem{'+bt.lower()+u'}[subsection]{'+bt[0].upper()+bt[1:].lower()+u'}\n';
            ret += u'\\newtheorem{'+bt.lower()+u'*}{'+bt[0].upper()+bt[1:].lower()+u'}\n';
    return ret


def build_headings(doc, position='before', format='css'):
    """ @position = 'before' (Theorem 3.1) / 'after' ( 3.1 Theorem ) """
    def walk(node):
        ret = set([])
        for child in node:
            if 'block' in child.get('class','').split(' '):
                ret.add(child.get('type',''))
            ret = ret.union(walk(child))
        return ret

    block_types = walk(doc)
    if format == 'css':
        return _css_from_blocktypes(block_types,position)
    elif format == 'latex':
        return _latex_from_blocktypes(block_types,position)

class EndOfDfBlockException(Exception):
    pass

class DefinitionBlockProcessor(BlockProcessor):

  START_RE = re.compile(r"""
      ^\s*                            # A definition block starts with possible whitespace,
      (?P<type>[^0-9\s:*]*)              # then comes the block type (e.g. theorem, example, etc.),
      (?P<do_not_number>\*)*          # an optional asterix indicating the block should not be numbered
      \s*
      (?:\((?P<name>[^)]*)\))*        # optional name in parenthesis,
      \s*
      (?:\[(?P<references>[^\]]*)\])* # optional references come in square brackegs (e.g. [ Balcar, Dow ]),
      \s*
      :                               # and finally a colon (with a possible asterix indicating no numbering)
      \s*                             # some whitespace (which will be discarded)
      (?P<rest>.*)                    # and the rest of the block
  """, re.VERBOSE | re.DOTALL)

  PROOF_REFERENCE_RE = re.compile(r"""\s*of\s* #(?P<id>[^\s]*)""")

  END_RE = re.compile(r'(.*){}\s*$', re.DOTALL)

  PROOFS = ['Proof']

  def _valid_type(self, tp, match):
      if not (tp[0].upper()==tp[0] and tp[1:].lower() == tp[1:]):
          return False
      if tp not in self.PROOFS:
          return True
      if match['references'] or match['name'] and not self.PROOF_REFERENCE_RE.match(match['name']):
          return False
      return True

  def test_start_block( self, parent, block ):
      match = self.START_RE.match(block)
      return match and self._valid_type(match.group('type'),match.groupdict())

  def test_end_block( self, parent, block ):
      return self.parser.state.isstate('definition_block') and self.END_RE.match(block)

  def test(self, parent, block):
      return self.test_start_block(parent, block) or self.test_end_block(parent, block)

  def add_info(self, element, match):
    el_classes = ['block',match['type']]

    # Add the 'do_not_number' css class to proofs
    # and unnumbered blocks (i.e. Theorem*, Definition*, etc)
    if match['do_not_number'] or match['type'] in self.PROOFS:
        el_classes.append('do_not_number')
    element.set('class',' '.join(el_classes))
    element.set('type',match['type'])

    # Add a heading element
    heading = etree.SubElement(element,'span')
    heading.set('class','block_heading')
    heading.set('type',match['type'])

    # Only non-proofs have authors, numbers and possible references
    if not match['type'] in self.PROOFS:
        # Add a number to the heading
        if not match['do_not_number']:
            number = etree.SubElement(heading,'span')
            number.set('class','block_number')

        # Add a name to the heading
        if match['name']:
            element.set('name',match['name'])
            name_heading = etree.SubElement(element,'span')
            name_heading.set('class','block_name')
            name_heading.text = match['name']

        # Add author references to the heading
        if match['references']:
            element.set('references',match['references'])
            ref_heading = etree.SubElement(element,'span')
            ref_heading.set('class','block_references')
            ref_heading.text = match['references']

    elif match['name']:
        key = self.PROOF_REFERENCE_RE.match(match['name']).groupdict()['id'];
        referenced_block = etree.SubElement(element,'span')
        referenced_block.text = 'of '
        ref = etree.SubElement(referenced_block,'ref')
        ref.set('key',key)

  def run(self, parent, blocks):
      # Process the first of the remaining blocks
      # (blocks are separated by blank lines)
      block = blocks.pop(0)

      # We are starting a new definition/lemma
      if self.test_start_block(parent,block):
          # Extract info about the definition/lemma, etc.
          m = self.START_RE.match(block).groupdict()
          typ = m['type']

          # Create a new div to hold this definition/lemma
          def_element = etree.SubElement(parent, 'div')

          # Add info about the element to the etree
          self.add_info(def_element,m)

          # Take the remainder of this block (i.e. withouth the
          # definition header) and add it to the list of blocks
          # to process
          blocks.insert(0,m['rest'])

          # Add a definition_block to the current state stack
          self.parser.state.set('definition_block')

          # Recursively process the blocks till we find
          # the end of this definition/lemma
          try:
              end_found = False
              self.parser.parseBlocks(def_element,blocks)
          except EndOfDfBlockException:
              end_found = True

          if not end_found:
              logger.warn("Unterminated definition block")

          # Pop the current definition_block from the state stack
          self.parser.state.reset()

          # Test whether we are ending a proof and
          # add a QED sign if yes
          if typ in self.PROOFS:
              qed = etree.SubElement(def_element,'span')
              qed.set('class','qed')

      # We are ending a definition/lemma
      else:

          last_text = self.END_RE.match(block).group(1)
          self.parser.parseBlocks(parent,[last_text])

          # there's no other way to exit the parseBlocks
          # completely except consuming all the blocks
          # (we still need them) or throwing an exception
          raise EndOfDfBlockException()



class DefinitionBlockExtension(markdown.Extension):
  def __init__(self,configs):
    pass

  def extendMarkdown(self,md,md_globals):
    self.md = md
    ext = DefinitionBlockProcessor(md.parser)
    md.parser.blockprocessors.add('definitionblock',ext, '_begin')

def makeExtension(configs={}):
  return DefinitionBlockExtension(configs=configs)
