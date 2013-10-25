import logging
from markdown.util import etree
import re

logger =  logging.getLogger(__name__)

class laTeXRenderer():
  def __init__(self):
    self.preserve_underscores = False

  def render(self, html ):
    tree = etree.fromstring(html.encode('utf-8'))
    return self._render(tree)

  def _sectionDepth(self,tag):
    if len(tag) != 2 or not tag.startswith('h'):
      return None
    try:
      return int(tag[1])-1
    except:
      return None

  def _escape(self,s):
    if s is None:
      return ''
    if self.preserve_underscores:
      ret = s
    else:
      ret=s.replace('_','\\'+'_')
    ret=ret.replace('&','\\&')
    return ret

  def _render(self, node):
    output=''
    for child in node:
      sec_depth = self._sectionDepth(child.tag)
      if sec_depth is not None:
        output+='\\'+"sub"*sec_depth+'section{'+self._escape(child.text)+self._render(child).strip()+'}\n'
      elif child.tag == 'label':
        output+='\\label{'+child.get('key','')+'}\n'
      elif child.tag == 'p':
        output+='\n\n'+self._escape(child.text)+self._render(child)+'\n\n'
      elif child.tag == 'div':
        classes = child.get('class','').split(' ')
        if 'block' in classes:
          classes.remove('block')
          name_ref = ','.join([child.get('name',''),child.get('references','')])
          if len(name_ref)>1:
            name_ref = '['+name_ref.strip(',')+']'
          else:
            name_ref=''
          environment_type = classes[0].lower()
          output +='\n\\begin{'+environment_type+'}'+name_ref+'\n'+self._escape(child.text).strip()+self._render(child).strip()+'\n\\end{'+environment_type+'}\n'
      elif child.tag == 'em':
        output+='\\emph{'+self._escape(child.text).strip()+self._render(child).strip()+'}'
      elif child.tag == 'strong':
        output+='{\\bf '+self._escape(child.text).strip()+self._render(child).strip()+'}'
      elif child.tag == 'ref':
        key = child.get('key','')
        output+='\\ref{'+key+'}'
      elif child.tag == 'mathjax':
        self.preserve_underscores=True
        output+=self._escape(child.text).strip()+self._render(child).strip()
        self.preserve_underscores=False
      elif child.tag == 'ul':
        output+='\\begin{itemize}\n  '+self._render(child).strip()+'\n\\end{itemize}'
      elif child.tag == 'li':
        output+='  \\item '+self._escape(child.text).strip()+self._render(child)
      else:
        output+=self._render(child)
      output += self._escape(child.tail)
    return output
