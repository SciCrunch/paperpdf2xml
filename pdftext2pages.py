import os
import argparse
from xml.etree.ElementTree import Element, SubElement
import xml.etree.ElementTree as ET
import utils

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', action='store', help="input PDF Text file", required=True)
    parser.add_argument('-o', action='store', help="output directory", required=True)

    args = parser.parse_args()

    pdf_file = args.i
    out_dir = args.o

    if not os.path.exists(out_dir):
        os.mkdir(out_dir)

    with open(pdf_file, 'r') as f:
        content = f.read()

    pages = content.split('\f')

    out_file = out_dir + "/pdf.xml"
    top = Element('pdf')
    for text in pages:
        for i in [1, 2, 3, 4, 5, 6, 7, 14, 15, 16, 17, 18, 19, 20, 21]:
            text = text.replace(chr(i), '')
        page_el = SubElement(top, 'page')
        page_el.text = text

    utils.indent(top)
    tree = ET.ElementTree(top)
    tree.write(out_file, encoding='UTF-8')
    print("wrote file:", out_file)
