import mimetypes
import re

def find_children_by_class(parent,cls):
    """ Returns a list of descendants of @parent having
        css class @cls in their clas list """
    ret = []
    for ch in parent:
        classes = ch.get('class','').split(' ')
        if cls in classes:
            ret.append(ch)
        ret += find_children_by_class(ch,cls)
    return ret

def get_by_id( elements, id ):
    """ Returns the element with id @id which is either in elements or
        a descendant of an element in elements. If there is no such element
        returns None """
    for e in elements:
        if e.get('id',None) == id:
            return e
        ret = get_by_id(e,id)
        if ret is not None:
            return ret
    return None

def section_level(node):
    """ Returns None if node is not a heading tag
        or the heading level """
    if len(node.tag) != 2 or not node.tag.startswith('h'):
      return None
    try:
      return int(node.tag[1])
    except:
      return None


URI_LAST_PART_RE = re.compile('.*?/*([^/]*)$')
EXTENSION_RE = re.compile('.*\.([^.]*)$')

def get_uri_info( uri ):
    """ Extracts some info from uri (filename, extension, mimetype)
        and returns it as a dict (with None values where no info is available) """
    ret = {}
    m = URI_LAST_PART_RE.match(uri)
    if m:
        ret['filename']=m.groups()[0]
        m = EXTENSION_RE.match(ret['filename'])
        if m:
            ret['extension']=m.groups()[0]
        else:
            ret['extension']=None
    else:
        ret['filename']=None
        ret['extension']=None
    mime_type, _ = mimetypes.guess_type(uri)
    ret['mimetype'] = mime_type or 'application/octet-stream'
    return ret
