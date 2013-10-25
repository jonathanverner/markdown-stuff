#!/usr/bin/python
import argparse
import os

import markdown
from markdown.util import etree
from  mdx_tolatex import laTeXRenderer
from mdx_defs import build_headings_css
import django.conf
import django.template
import logging

logging.basicConfig()
django.conf.settings.configure()

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
  parser.add_argument('--verbose', '-v', action='count',help='be verbose',default=0)
  parser.add_argument('document',type=argparse.FileType('r'),help='filename of the document to transform')

  args = parser.parse_args()
  logger =  logging.getLogger(__name__)
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

  tpl = django.template.Template(template)


  md = markdown.Markdown(extensions=['extra','defs','mymathjax','outline','semanticwikilinks','headerid','references','meta'])
  html = md.convert( unicode(args.document.read(),encoding='utf-8',errors='ignore') )
  html_tree = etree.fromstring((u'<html><head></head><body>'+html+u'</body></html>').encode('utf-8'))

  dct = {}
  if args.format == 'html':
    output = html
    dct['headings_css'] = build_headings_css(html_tree,position='after')
  elif args.format == 'latex':
    latex = laTeXRenderer()
    output = latex.render(html)

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

  output = tpl.render(django.template.Context(dct))

  if args.output:
    args.output.write(output.encode('utf-8'))
  else:
    print output.encode('utf-8')

if __name__ == "__main__":
  main()










