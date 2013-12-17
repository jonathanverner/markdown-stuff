import logging
import os
from markdown.util import etree
import re

logger =  logging.getLogger(__name__)

class laTeXRenderer(object):
  def __init__(self, options = None):
      if options:
          self.options = options
      else:
          self.options = {}
      self.preserve_underscores = False

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
    if self.preserve_underscores:
      ret = s
    else:
      ret=s.replace('_','\\'+'_')
    return ret

  def _render(self, node):
    output=''
    for child in node:
      sec_depth = self._sectionDepth(child.tag)
      if sec_depth is not None:
          if 'do_not_number' in child.get('class',''):
              output+='\\'+"sub"*sec_depth+'section*{'+self._escape(child.text)+self._render(child).strip()+'}\n'
          else:
              output+='\\'+"sub"*sec_depth+'section{'+self._escape(child.text)+self._render(child).strip()+'}\n'
      elif child.tag == 'label':
        output+='\\label{'+child.get('key','')+'} '
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
      elif 'qed' in child.get('class',''):
          if 'nested' in child.get('class',''):
              output+=r'\renewcommand{\qedsymbol}{$\blacksquare$}'+"\n"
      elif child.tag == 'em':
        output+='\\emph{'+self._escape(child.text).strip()+self._render(child).strip()+'}'
      elif child.tag == 'strong':
        output+='{\\bf '+self._escape(child.text).strip()+self._render(child).strip()+'}'
      elif child.tag == 'ref':
        key = child.get('key','')
        output+='\\ref{'+key+'}'
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
        self.preserve_underscores=True
        output+=self._escape(child.text).strip()+self._render(child).strip()
        self.preserve_underscores=False
      elif child.tag == 'ul':
        output+='\\begin{itemize}\n  '+self._render(child).strip()+'\n\\end{itemize}'
      elif child.tag == 'ol':
        output+='\\begin{enumerate}\n  '+self._render(child).strip()+'\n\\end{enumerate}'
      elif child.tag == 'li':
        output+='  \\item '+self._escape(child.text).strip()+self._render(child)
      elif child.tag == 'blockquote':
        output+='\\begin{quotation}\n  '+self._render(child).strip()+'\n\\end{quotation}'
      else:
        output+=self._render(child)
      output += self._escape(child.tail)
    return output
