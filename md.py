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

try:
    from jinja2 import Template
    Environment(extensions=['jinja2.ext.autoescape'])
    template_system = "JINJA2"
except:
    pass




def render_template(tpl, context):
    if template_system == "DJANGO":
        dtpl = django.template.Template(tpl)
        return dtpl.render(django.template.Context(context))

    elif template_system == "JINJA2":
        dtpl = Template(tpl)
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

  md = markdown.Markdown(extensions=['extra','defs','mymathjax','wikilinks','headerid','references','meta'])
  doc = unicode(args.document.read(),encoding='utf-8',errors='ignore')
  doc = mdx_macros.pre_process(doc)
  html = md.convert( doc )

  if args.query:
      try:
          selector = CSSSelector(args.query)
      except Exception, e:
          logger.critical("Error parsing query: "+args.query+" ("+str(e)+")")
          exit(-1)
      html_tree = lxml.etree.fromstring((u'<html><head></head><body>'+html+u'</body></html>').encode('utf-8'))
      for e in selector(html_tree):
          print e.tag, e.attrib
          if args.full:
              print "-"*80
              print text_content(e),
              print "-"*80
      return

  if args.filter:
      try:
          selector = CSSSelector(args.filter)
      except Exception, e:
          logger.critical("Error parsing filter: "+args.query+" ("+str(e)+")")
          exit(-1)
      html_tree = lxml.etree.fromstring((u'<html><head></head><body>'+html+u'</body></html>').encode('utf-8'))
      html = '\n'.join([lxml.etree.tostring(e) for e in selector(html_tree)])


  html_tree = etree.fromstring((u'<html><head></head><body>'+html+u'</body></html>').encode('utf-8'))

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










