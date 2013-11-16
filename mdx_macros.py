#! /usr/bin/env python


'''
Macros Extension for TMD
========================

Adds support for macros.


Usage
-----

'''

import logging
import re


logger =  logging.getLogger(__name__)


ABBREVS_RE = re.compile(r"""\s*={3,}\s*Abbreviations\s*={3,}\s*\n(?P<abbrevs>.*)\n\s*={3,}\s*Abbreviations\s*={3,}\s*""",re.DOTALL | re.UNICODE | re.MULTILINE | re.IGNORECASE)
ABBREV_RE  = re.compile(r"""\s*\\(?P<name>\w+)(?P<args>\([^)]*\))?\s*=\s*{(?P<body>.*?)};\n\s*""",re.DOTALL | re.UNICODE | re.MULTILINE | re.IGNORECASE)

class macro(object):

    def _arg_pattern(self,name,optional=True):
        ret = r"(?P<"+name+"full>(?P<"+name+"br>{[^}]*})|(?P<"+name+"comma>[^,)]*))"
        if optional:
            ret = ret + '?'
        return ret

    def __init__(self, name, args, body):
        self.name = name.strip()
        self.body = body
        self.args = {}
        self.invalid = False
        if len(self.name) == 0:
            self.invalid = True
            return
        pattern = r'\\'+self.name
        if args:
            optional = False
            required_args = []
            optional_args = []
            for arg in args.strip('()').split(','):
                arg = arg.strip()
                if optional and not '=' in arg:
                    self.invalid = True
                    logger.warn("arg " + arg + " is optional and must have a default value")
                if optional or '=' in arg:
                    optional = True
                    name, default_value = arg.split('=')
                    name = name.strip()
                    optional_args.append(self._arg_pattern(name,optional=True))
                else:
                    name, default_value = arg, None
                    required_args.append(self._arg_pattern(name,optional=False))
                self.args[name]=default_value
            pattern = pattern + r'\('+','.join(required_args)
            if len(optional_args) > 0:
                pattern = pattern + ',?'+',?'.join(optional_args)+r'\)'
            else:
                pattern = pattern + r'\)'
        pattern = pattern+'(?![A-Za-z])'
        self.macro_pattern = re.compile(pattern)

    def _repl(self, match):
        d = match.groupdict()
        ret = self.body
        for name, default in self.args.items():
            val = d[name+'br'] or d[name+'comma'] or default
            if not val:
                logger.warn("value not supplied for argument "+name)
                val = ''
            ret = ret.replace(name, val)
        return ret

    def apply(self, document):
        if self.invalid:
            return document
        return self.macro_pattern.sub(self._repl,document)

def pre_process(document):
    m = ABBREVS_RE.search(document)
    if not m:
        return document
    document = ABBREVS_RE.sub('\n\n',document)
    abbrevs = m.groupdict()['abbrevs']
    macros = {}
    for abbrev in ABBREV_RE.finditer(abbrevs):
        d = abbrev.groupdict()
        macros[d['name']] = macro(d['name'],d['args'],d['body'])

    for m in macros.values():
        document = m.apply(document)

    return document
