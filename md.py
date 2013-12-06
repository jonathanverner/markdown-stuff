#!/usr/bin/python
import argparse
import os
import re

import markdown
from markdown.util import etree
import lxml
from lxml.cssselect import CSSSelector
from  mdx_tolatex import laTeXRenderer
from mdx_defs import build_headings
import logging
import mdx_macros

template_system = None
try:
    import django.conf
    import django.template

    logging.basicConfig()
    django.conf.settings.configure()
    template_system = "DJANGO"
except:
    pass

if not template_system:
    try:
        from jinja2 import Template
        import jinja2
        jinja_env=jinja2.Environment(extensions=['jinja2.ext.autoescape'])
        template_system = "JINJA2"
    except:
        pass




def render_template(tpl, context):
    if template_system == "DJANGO":
        dtpl = django.template.Template(tpl)
        return dtpl.render(django.template.Context(context))

    elif template_system == "JINJA2":
        dtpl = jinja_env.Template(tpl)
        return dtpl.render(context)
    else:
        logging.getLogger("md").warn("No template library found!")
        for (key,value) in context.items():
            exp = re.compile(r"{{\s*"+key+"\s*}}",re.UNICODE | re.IGNORECASE)
            tpl=exp.sub(value.replace("\\", "\\\\"),tpl)
        exp = re.compile("{%[^%]*%}")
        tpl = exp.sub("",tpl)
        return tpl

def text_content(element):
    ret = ''
    if element.text:
        ret += element.text
    for c in element:
        ret += ' '+ text_content(c)
    if element.tail:
        ret += element.tail
    return ret

def parse_html( html, tree ):
    """ Parses html as an
           - lxml.etree (@tree='lxml')
           - markdown.util.etree (@tree='md')
    """
    if tree == 'lxml':
        return lxml.etree.fromstring((u'<html><head></head><body>'+html+u'</body></html>').encode('utf-8'))
    else:
        return etree.fromstring((u'<html><head></head><body>'+html+u'</body></html>').encode('utf-8'))

def render_md( md_text, tree = None ):
    """ Converts the (unicode) markdown @md_text to html.
        And returns the pair (md,html) where
          md is the resulting parser instance
        and the html is
             - html string (@tree = None)
             - parsed lxml.etree (@tree='lxml')
             - parsed markdown.util.etree (@tree='md')
    """
    md = markdown.Markdown(extensions=['extra','defs','mymathjax','wikilinks','headerid','references','meta'])
    doc = mdx_macros.pre_process(md_text)
    html = md.convert(doc)
    if tree:
        return md, parse_html(html, tree)
    else:
        return md, html

def filter(css_selector, lxmltree):
    """ Returns an iterable over the elements from @lxmltree matching
        the css selector @css_selector
    """
    try:
        selector = CSSSelector(css_selector)
        return selector(lxmltree)
    except Exception, e:
        logger.critical("Error parsing filter: "+css_selector+" ("+str(e)+")")
        return []

def query( css_selector, lxmltree ):
    """ Returns a list of maps containing the properties of elements
        from @lxmltree matching the @css_selector. Each map moreover
        contains a 'tag' key (with the respective element tagname) and
        a 'text_content' key (with the text content of the element).
    """
    ret = []
    for e in filter(css_selector,lxmltree):
        e_map = {
            'tag':e.tag,
            'text_content':text_content(e)
        }
        e_map.update(e.attrib)
        ret.append( e_map )
    return ret



def main():
  format_exts = {
    'html':'html',
    'latex':'tex'
  }
  default_tplfname = os.environ['HOME']+'/.md/default-template'

  parser = argparse.ArgumentParser(description='A markdown processor')
  parser.add_argument('-t', '--template', help='document template')
  parser.add_argument('-o', '--output', type=argparse.FileType('w'),help='output file')
  parser.add_argument('-f', '--format',help='output format', choices=['html','latex'],default='html')
  parser.add_argument('-s', '--subs',help='template substitutions',default='')
  parser.add_argument('--filter',help='process only elements matching a given css selector',default=None)
  parser.add_argument('-q', '--query',help='print out elements matching a given css selector')
  parser.add_argument('--attrs', help='a comma separated list of attribute names to print (in conjunction with -q)', default='text_content')
  parser.add_argument('--full',help='print out elements matching a given css selector',action='store_true')
  parser.add_argument('--verbose', '-v', action='count',help='be verbose',default=0)
  parser.add_argument('document',type=argparse.FileType('r'),help='filename of the document to transform')

  args = parser.parse_args()
  logger =  logging.getLogger("md")
  root_logger = logging.getLogger()
  root_logger.setLevel(logging.FATAL-args.verbose*10)

  if not args.template:
    try:
      template = unicode(file(default_tplfname+'.'+format_exts[args.format],'r').read(),encoding='utf-8',errors='ignore')
    except:
      logger.warn('Could not open default ')
      template = '{{ content }}'
  else:
    try:
      template = unicode(file(args.template,'r').read(),encoding='utf-8',errors='ignore')
    except Exception,e:
      logger.critical('Could not open template file'+str(e))
      exit(-1)

  md, html = render_md(unicode(args.document.read(),encoding='utf-8',errors='ignore'),tree=None)

  if args.query:
      html_tree = parse_html(html,tree='lxml')
      attrs = args.attrs.split(',')
      for e in query(args.query, html_tree):
          print ','.join([ attr+'='+e[attr] for attr in attrs if attr in e ])
      return

  if args.filter:
      html_tree = parse_html(html,tree='lxml')
      html = '\n'.join([lxml.etree.tostring(e) for e in filter(args.filter, html_tree)])


  html_tree = parse_html(html,tree='md')

  dct = {}

  if args.format == 'html':
    output = html
    dct['headings_css'] = build_headings(html_tree,position='after',format='css')
  elif args.format == 'latex':
    dct['headings'] = build_headings(html_tree,position='after',format='latex')
    latex = laTeXRenderer()
    output = latex.render_from_dom(html_tree)

  dct['content']=output
  for (k,v) in md.Meta.items():
    dct[k] = ' '.join(v)

  dct['toc']=etree.tostring(md.TOC.to_element())

  try:
      for l in open('.md-substitutions','r').readlines():
          if l.strip().startswith('#'):
              continue
          try:
              k,v = l.strip().split('=')
              dct[k.strip()] = v.strip()
          except:
              pass
  except:
      pass

  if args.subs:
      for ts in args.subs.split(','):
          k,v = ts.split('=')
          dct[k] = v

  if 'image_path' in dct:
      exp = re.compile(r'(<img\s*[^>]*)\s*src=[\'"]([^\'"]*)[\'"]([^>]*>)')
      dct['content']=exp.sub(r'\1src="'+dct['image_path']+r'\2"\3',dct['content'])

  output = render_template(template, dct)

  if args.output:
    args.output.write(output.encode('utf-8'))
  else:
    print output.encode('utf-8')

if __name__ == "__main__":
  main()










