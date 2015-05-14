import lxml.etree as etree

import logging
logger =  logging.getLogger(__name__)

from utils import find_children_by_class, section_level


def new_section(parent, h_node):
    """ Creates a new section as a child of parent
        from the heading node @h_node """
    sec = etree.SubElement(parent,'section')
    sec_numbers = find_children_by_class(h_node,'section_number')
    sec.set('level',str(section_level(h_node)))
    if len(sec_numbers) > 0:
        sec.set('number',sec_numbers[0].text)
        sec.set('title',sec_numbers[-1].tail)
    return sec


def build_sections(html_tree):
    """ Wraps each heading together with what fallows
        into an appropriate <section> node """
    top_section = etree.Element('section')
    section_stack = []
    current_section = top_section
    current_level = 0
    for node in html_tree.find('body'):
        level = section_level(node)
        if level is None:
            # node is not a heading, so we append it to the current section """
            current_section.append(node)
        else:
            if level > current_level:
                # Add the current section to the stack and create
                # a new subsection which will be the new current_section
                section_stack.append((current_section,current_level))
                current_section = new_section(current_section,node)
                current_level = level
            elif level <= current_level:
                # Back up the stack until we reach the current level
                while level < current_level:
                    current_section, current_level = section_stack.pop()
                # Create a new current section
                parent_section = section_stack[-1][0]
                current_section = new_section(parent_section,node)
            current_section.append(node)



    return top_section