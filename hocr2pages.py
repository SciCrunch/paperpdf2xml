import re
import argparse

from xml.etree.ElementTree import Element, SubElement
import xml.etree.ElementTree as ET
import utils

class BBox(object):
    def __init__(self, y0, x0, y1, x1, node):
        self.y0 = y0
        self.x0 = x0
        self.y1 = y1
        self.x1 = x1
        self.node = node

    def __str__(self):
        return str(self.y0) + ' ' + str(self.x0) + ' ' + str(self.y1) + ' ' + str(self.x1)

    def __repr__(self):
        return self.__str__()

    @classmethod
    def from_node(cls, node):
        bbox_str = node.attrib['title']
        tokens = bbox_str.split()
        assert  len(tokens) == 5 and tokens[0] == 'bbox'
        return cls(int(tokens[1]), int(tokens[2]), int(tokens[3]),
                   int(tokens[4]), node)


class Cluster(object):
    def __init__(self, label):
        self.label = label
        self.members = []
        self.y0min, self.x0min, self.x1max, self.y1max = 10000, 10000, 0, 0

    def add_member(self, member: BBox):
        self.members.append(member)
        for m in self.members:
            if self.y0min > m.y0:
               self.y0min = m.y0
            if self.x0min > m.x0:
                self.x0min = m.x0
            if self.x1max < m.x1:
                self.x1max = m.x1
            if self.y1max < m.y1:
                self.y1max = m.y1

    def __str__(self):
        return '[%s %s %s %s]' % (self.y0min, self.x0min, self.y1max, self.x1max )

    def __repr__(self):
        return self.__str__()

    def belongs(self, candidate: BBox):
        if not self.members:
            return True
        # print('{} =? {}'.format( self.members[0].y0, candidate.y0))
        adiff =  abs(self.members[0].y0 - candidate.y0)
        return adiff <= 1

    def get_y0(self):
        return self.members[0].y0

    def size(self):
        return len(self.members)

    def area(self):
        return (self.y1max - self.y0min) * (self.x1max - self.x0min)


    def grow2(self, clusters, ymin, ymax):
        grown = False
        for c in clusters:
            for m in c.members:
                if m.y1 < ymax and m.y0 > ymin:
                    self.add_member(m)
                    grown = True
        if grown:
            self.members.sort(key= lambda x: x.x0)


    def grow(self, clusters):
        grown = False
        for c in clusters:
            for m in c.members:
                # print('>> ', m, 'is in ', self)
                if self.is_inside(m):
                    self.add_member(m)
                    grown = True
        if grown:
            self.members.sort(key=lambda x: x.x0)

    def is_inside(self, candidate: BBox):
        c = candidate
        x0, y0, x1, y1 = c.x0, c.y0, c.x1, c.y1
        xmid = x0 + (x1 - x0)/2
        ymid = y0 + (y1 - y0)/2
        #return self.y0min <= y0 and self.y1max >= y1 and self.x0min <= x0 and self.x1max >= x1
        return self.y0min <= ymid and self.y1max >= ymid and self.x0min <= xmid and self.x1max >= xmid


    def get_text(self):
        lines = []
        for m in self.members:
            collect_text(m.node, lines)
        # broken (hyphenated) word fix
        num_lines = len(lines)
        for i, line in enumerate(lines):
            if len(line) == 0:
                continue
            next_tok = lines[i+1][0] if i+1 < num_lines else None
            if line[-1].endswith('-') and next_tok and str(next_tok[0]).islower():
                line[-1] =  line[-1][:-1] + lines[i+1][0]
                del lines[i+1][0]


        content = ""
        for line in lines:
            content += " ".join(line) + "\n"
        return content

def remove_figure_captions(content):
    p = re.compile(r"^Figure\s+\d+(?:-\d+)\s+[A-Z].+(\n?.+)?\.", re.MULTILINE)
    s = re.sub(p, '', content)
    return s


def is_eligible(node):
    if 'pdftotree' not in node.attrib:
        return True
    attr = node.attrib['pdftotree']
    # return attr != 'figure_caption' and attr != 'header' and attr != 'table_caption'
    if attr == 'section_header':
        lines = []
        collect_all_text(node, lines)
        content = ""
        for line in lines:
            content += " ".join(line) + "\n"
        content = content.rstrip()
        if content.isnumeric():
            return False
        if content.find('All rights reserved') != -1:
            return False
        if content.find('U n i t') != -1:
            return False

    return attr != 'figure_caption' and attr != 'header'


def collect_all_text(node, lines):
    if  node.tag == 'div':
        for child in node:
            collect_text(child, lines)
    elif node.tag == 'span':
        if node.attrib['class'] == 'ocrx_line':
            lines.append([])
            for child in node:
                collect_text(child, lines)
        elif node.attrib['class'] == 'ocrx_word':
            lines[-1].append(node.text)


def collect_text(node, lines):
    if  node.tag == 'div':
       if is_eligible(node):
           for child in node:
               collect_text(child, lines)
    elif node.tag == 'span':
        if node.attrib['class'] == 'ocrx_line':
            lines.append([])
            for child in node:
                collect_text(child, lines)
        elif node.attrib['class'] == 'ocrx_word':
            lines[-1].append(node.text)


def cluster_bboxes(bbox_list, top_el=None):
    clusters = []
    for bbox in bbox_list:
        closest = None
        for  c in clusters:
            if c.belongs(bbox):
                closest = c
                break
        if closest:
            closest.add_member(bbox)
        else:
            c = Cluster(bbox.y0)
            c.add_member(bbox)
            clusters.append(c)
    for c in clusters:
        print("Cluster {} - members:{} {}".format(c.label, len(c.members), c))
    print('-'*80)
    ct = find_columns(clusters)
    if ct:
        ymid = ct[0].y1max + (ct[1].y0min - ct[0].y1max)/2
        ymax = ct[1].y1max + 50
        clist = list(clusters)
        clist.remove(ct[0])
        clist.remove(ct[1])
        ct[0].grow2(clist, 0, ymid)
        ct[1].grow2(clist, ymid, ymax)
        print("Left Column Cluster {} - members:{} {}".format(ct[0].label, len(ct[0].members), ct[0]))
        print("Right  Column Cluster {} - members:{} {}".format(ct[1].label, len(ct[1].members), ct[1]))

        content = ""
        print("Left Column\n---------\n")
        col_text = ct[0].get_text()
        content += col_text
        print(col_text)
        print("\nRight Column\n---------\n")
        col_text = ct[1].get_text()
        content += col_text
        print(col_text)
        if top_el is not None:
            page_el = SubElement(top_el, 'page')
            page_el.text = content

    print('-'*80)


def find_columns(clusters):
    if len(clusters) < 2:
        return None
    clist = list(clusters)
    # clist.sort(reverse=True, key=lambda x: len(x.members))
    clist.sort(reverse=True, key=lambda x: x.area())
    # two column assumption
    col1, col2 = clist[0], clist[1]
    if col1.size() == 1 or col2.size() ==1 :
        return None
    return (col1, col2) if col1.get_y0() < col2.get_y0() else (col2, col1)



def handle_page(node, num_cols=2, top_el=None):
    bbox_list = []
    for child in node:
        if child.tag != 'div':
            continue
        bbox = BBox.from_node(child)
        bbox_list.append(bbox)
    print('# boxes:', len(bbox_list))
    cluster_bboxes(bbox_list, top_el=top_el)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', action='store', help="input HOCR html file", required=True)
    parser.add_argument('-o', action='store', help="output text XML file", required=True)

    args  = parser.parse_args()

    hocr_file = args.i
    out_xml_file = args.o
    tree = ET.parse(hocr_file)
    top = Element('pdf')
    for node in tree.findall('.//body/div'):
        handle_page(node, top_el=top)
    utils.indent(top)
    out_tree = ET.ElementTree(top)
    out_tree.write(out_xml_file, encoding="UTF-8")
    print("wrote file:", out_xml_file)



def test_driver():
    tree = ET.parse('x.html')
    for node in tree.findall('.//body/div'):
        print (node.attrib)
        handle_page(node)


if __name__ == '__main__':
    main()
