import re
import markdown

class MathJaxDollarPattern(markdown.inlinepatterns.Pattern):
    PATBRACE   = r'((?<!\\)(?P<lbrace>\\\()(?P<contentA>.+?)(?P<rbrace>\\\)))'
    PATBRACKET = r'((?<!\\)(?P<lbracket>\\\[)(?P<contentB>.+?)(?P<rbracket>\\\]))'
    PATDOLLAR  = r'((?<!\\)(?P<dollar>\$\$?)(?P<contentC>.+?)(?P=dollar))'
    PAT        = '(('+PATBRACE +')|('+PATDOLLAR+')|('+PATBRACKET+'))'

    def __init__(self):
        markdown.inlinepatterns.Pattern.__init__(self, self.PAT)

    def handleMatch(self, m):
        node = markdown.util.etree.Element('mathjax')
        d = m.groupdict()
        if d['lbrace']:
            start = '\\('
            end = '\\)'
            content = d['contentA']
        elif d['dollar']:
            start = end = d['dollar']
            content = d['contentC']
        else:
            start = '\\['
            end = '\\]'
            content = d['contentB']
        node.text = markdown.util.AtomicString(start + content + end)
        return node

class MathJaxExtension(markdown.Extension):
    def extendMarkdown(self, md, md_globals):
        # Needs to come before escape matching because \ is pretty important in LaTeX
        md.inlinePatterns.add('mymathjax', MathJaxDollarPattern(), '<escape')

def makeExtension(configs=None):
    return MathJaxExtension(configs)


