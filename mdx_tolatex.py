import logging
import os
from markdown.util import etree
import re

from utils import get_uri_info, get_child_by_css_selector

logger =  logging.getLogger(__name__)

class laTeXRenderer(object):
  IGNORE_CLASSES = ['section_number','reference_number','block_number', 'block_name','block_references']

  def __init__(self, options = None):
      if options:
          self.options = options
      else:
          self.options = {}
      self.math_mode = False

  def render_from_HTML(self, html ):
    tree = etree.fromstring(html.encode('utf-8'))
    return self.render_from_dom(tree)

  def render_from_dom(self, dom_tree ):
    return self._render(dom_tree)

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
    ret = s
    if not self.math_mode:
      ret = ret.replace('_','\\'+'_')
      ret = ret.replace('&','\\'+'&')
      ret = ret.replace('%','\\'+'%')
      ret = ret.replace('\\','\\textbackslash{}')
    return ret

  def _ignore_node(self,node):
      for node_c in node.get('class','').split(' '):
          if node_c in self.IGNORE_CLASSES:
              return True
      return False

  def _render(self, node, ignore_info_nodes = True):
    if  ignore_info_nodes and self._ignore_node(node):
        return ''
    output=self._escape(node.text)+' '
    for child in node:
      sec_depth = self._sectionDepth(child.tag)
      if sec_depth is not None:
          if 'do_not_number' in child.get('class',''):
              output+='\\'+"sub"*sec_depth+'section*{'+self._render(child).strip()+'}\n'
          else:
              output+='\\'+"sub"*sec_depth+'section{'+self._render(child).strip()+'}\n'

      elif child.tag == 'label':
        output+='\\label{'+child.get('key','')+'} '
      elif child.tag == 'p':
        output+='\n\n'+self._render(child)+'\n\n'
      elif child.tag == 'div':
        classes = child.get('class','').split(' ')
        if 'block' in classes:
          classes.remove('block')
          environment_type = classes[0].lower()
          if 'do_not_number' in classes and environment_type != 'proof':
            environment_type +='*'
          block_name_tag = get_child_by_css_selector(child, '.block_name')
          block_refs_tag = get_child_by_css_selector(child, '.block_references')
          name_ref = []
          if block_name_tag is not None:
              name_ref.append(self._render(block_name_tag, ignore_info_nodes=False).strip())
          if block_refs_tag is not None:
              name_ref.append(self._render(block_refs_tag, ignore_info_nodes=False).strip())
          name_ref = ','.join(name_ref)
          if len(name_ref)>0:
              if environment_type == 'proof':
                  name_ref = '[Proof '+name_ref+']'
              else:
                  name_ref = '['+name_ref+']'
          output +='\n\\begin{'+environment_type+'}'+name_ref+'\n'+self._render(child).strip()+'\n\\end{'+environment_type+'}\n'
      elif 'qed' in child.get('class',''):
          if 'nested' in child.get('class',''):
              output = output.strip()+r'\renewcommand{\qedsymbol}{$\blacksquare$}'+"\n"
      elif child.tag == 'em':
        output+='\\emph{'+self._render(child).strip()+'}'
      elif child.tag == 'strong':
        output+='{\\bf '+self._render(child).strip()+'}'
      elif child.tag == 'ref':
        key = child.get('key','')
        output+='\\ref{'+key+'}'
      elif child.tag == 'bib':
        key = child.get('key','')
        output+='\\cite{'+key+'}'
      elif child.tag == 'a':
          # FIXME:
          # Here we are relying on the fact that
          # we have already processed <ref> tags, so
          # this <a> element is not a descendant of a <ref> tag
          # so it should point to somewhere out of this document.
          url = child.get('href')
          render_chld = self._render(child)
          if child.text:
              txt = child.text + render_chld
          else:
              txt = render_chld
          txt = txt.strip()
          if len(txt) > 0:
              output+='\\href{'+url+'}{'+txt+'}'
          else:
              output+='\\url{'+url+'}'
          if 'attach_files' in self.options:
              info = get_uri_info(url)
              if info['filename']:
                  output+='\\incfile{'+txt+'}{'+str(info['filename'])+'}{'+str(info['mimetype'])+'}'

      elif child.tag == 'img':
          fname = child.get('src')
          ext = ''
          for i in range(1,len(fname)+1):
              ext=fname[-i]+ext
              if fname[-i] == '.':
                  break
          base = fname[:-len(ext)]
          if os.path.exists(base+'.pdf'):
              fname = base+'.pdf'
          output+='\\begin{center}\\includegraphics{'+fname+'}\\end{center}'
      elif child.tag == 'mathjax':
        self.math_mode=True
        output+=self._render(child).strip()
        self.math_mode=False
      elif child.tag == 'ul':
        output+='\\begin{itemize}\n  '+self._render(child).strip()+'\n\\end{itemize}'
      elif child.tag == 'ol':
        output+='\\begin{enumerate}\n  '+self._render(child).strip()+'\n\\end{enumerate}'
      elif child.tag == 'li':
        output+='  \\item '+self._render(child)
      elif child.tag == 'blockquote':
        output+='\\begin{quotation}\n  '+self._render(child).strip()+'\n\\end{quotation}'
      else:
        output+=self._render(child)
      output +=self._escape(child.tail)
    return output
