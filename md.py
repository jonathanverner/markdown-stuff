#!/usr/bin/python
import argparse
import os
import re

import markdown
from markdown.util import etree
import lxml
import lxml.etree
from lxml.cssselect import CSSSelector

from  mdx_tolatex import laTeXRenderer
from mdx_defs import build_headings
from postprocess import build_sections
from utils import get_by_id
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

logger = logging.getLogger("md")
root_logger = logging.getLogger()


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
    """ Returns the contents of the element @element
        converted to plain text """
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

def filter(css_selector, lxmltree, include_references = True):
    """ Returns an iterable over the elements from @lxmltree matching
        the css selector @css_selector. If @include_references is True,
        the iterable will contain an additional <references> element
        which will contain all referenced elements not already present.
    """
    try:
        selector = CSSSelector(css_selector)
        if include_references:
            refs_selector = CSSSelector('ref')
            ref_ids = set([])
            ret = []
            # Find all references in the selected elements
            # and store the referenced urls (should be of the form #id)
            # in ref_ids
            for ch in selector(lxmltree):
                ret.append(ch)
                for ref_node in refs_selector(ch):
                    a_nodes = ref_node.findall('a')
                    if len(a_nodes) > 0:
                        ref_ids.add(a_nodes[-1].get('href',None))
            if len(ref_ids) > 0:
                # Create the <references> element and an appropriate heading for it
                ref_parent = lxml.etree.Element('references')
                ref_h = lxml.etree.SubElement(ref_parent,'h1')
                ref_h.set('class','do_not_number')
                ref_h.text = 'References'
                references_found = False

                # Iterate over the reference ids and check that they exist
                # and are not already present in the selected elements
                for id in sorted(ref_ids):
                    if id:
                        logger.debug("Checking reference "+id)
                        # Only include the reference if it is not already present in the selected elements
                        if get_by_id(selector(lxmltree),id[1:]) is None:
                            logger.debug("Adding reference "+id)
                            ref = get_by_id(lxmltree,id[1:])
                            if ref is None:
                                logger.warn("Reference "+id+" not found")
                            else:
                                references_found = True
                                ref_parent.append(ref)
                # Do not include the <references> element if there were no references
                if references_found:
                    ret.append(ref_parent)
            return ret
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
  parser.add_argument('--norefs',help='do not include referenced elements when filtering',action='store_true')
  parser.add_argument('--verbose', '-v', action='count',help='be verbose',default=0)
  parser.add_argument('--renderoptions', help='a comma separated list of key=value pairs which will be passed as options to the renderer',default=None)
  parser.add_argument('document',type=argparse.FileType('r'),help='filename of the document to transform')

  args = parser.parse_args()

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

  md, lxml_tree = render_md(unicode(args.document.read(),encoding='utf-8',errors='ignore'),tree='lxml')
  lxml_tree = build_sections(lxml_tree)

  if args.query:
      attrs = args.attrs.split(',')
      for e in query(args.query, lxml_tree):
          print ','.join([ attr+'='+e[attr] for attr in attrs if attr in e ])
      return

  if args.filter:
      html = '\n'.join([lxml.etree.tostring(e,method='html') for e in filter(args.filter, lxml_tree, include_references=not args.norefs)])
  else:
      html = lxml.etree.tostring(lxml_tree,method='html')

  html_tree = parse_html(html,tree='md')

  dct = {}
  render_options = {}
  if args.renderoptions:
    try:
        for opt in args.renderoptions.split(','):
            key,value = opt.split('=')
            render_options[key]=eval(value)
    except Exception, e:
        logger.warn('Bad render options: '+args.renderoptions+' ('+str(e)+')')

  if args.format == 'html':
    output = html
    dct['headings_css'] = build_headings(html_tree,position='after',format='css')
  elif args.format == 'latex':
    dct['headings'] = build_headings(html_tree,position='after',format='latex')
    latex = laTeXRenderer(render_options)
    output = latex.render_from_dom(html_tree)

  dct['content']=output
  if hasattr(md, 'Meta'):
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










