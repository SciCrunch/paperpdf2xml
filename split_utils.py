from xml.etree.ElementTree import Element, SubElement
import xml.etree.ElementTree as ET
import os.path
import utils
import numpy as np
from junk_remover import extract_page_sections


class PageStats(object):
    def __init__(self, page_no, sections):
        self.page_no = page_no
        self.sections = sections
        self.num_bad_lines, self.num_good_lines = 0, 0
        self.total = 0
        for section in sections:
            self.total += len(section.lines)
            if section.sec_type == 'bad':
                self.num_bad_lines += len(section.lines)
            else:
                self.num_bad_lines += len(section.lines)


def prep_page_stats(xml_file):
    page_sections = extract_page_sections(xml_file)
    pg_list = [PageStats(pn, sections) for pn, sections in page_sections.items()]
    return pg_list


def write_page_range(out_file, pg_list, start, end):
    top = Element('pdf')
    for i in range(start, end):
        pg = pg_list[i]
        content = ""
        for section in pg.sections:
            if section.sec_type == 'bad':
                nl = len(section.lines)
                for j, line in enumerate(section.lines):
                    if j == 0:
                        content += '{junk}' + line + "\n"
                    elif j == nl - 1:
                        content += line + "{junk}\n"
                    else:
                        content += line + "\n"
            else:
                for line in section.lines:
                    content += line + "\n"
        page_el = SubElement(top, 'page')
        page_el.text = content
    utils.indent(top)
    out_tree = ET.ElementTree(top)
    out_tree.write(out_file, encoding="UTF-8")
    print("wrote file:", out_file)


def prep_splits(pg_list, out_dir, prefix):
    # total = sum(pg.total for pg in pg_list)
    bad_total = sum(pg.num_bad_lines for pg in pg_list)
    cum_bad_total = 0
    i = 0
    for frac in np.arange(0.1, 1.0, 0.1):
        target = frac * bad_total
        while cum_bad_total < target:
            cum_bad_total += pg_list[i].num_bad_lines
            i += 1
        percent = str(int(cum_bad_total / float(bad_total) * 100))
        train_file = os.path.join(out_dir,
                                  prefix + '_train_' + percent + ".xml")
        test_file = os.path.join(out_dir,
                                 prefix + '_test_' + percent + ".xml")
        write_page_range(train_file, pg_list, 0, i)
        write_page_range(test_file, pg_list, i, len(pg_list))


if __name__ == '__main__':
    in_file = 'data/annotations/Unit_IX_The_Nervous_System_A.xml'
    pg_list = prep_page_stats(in_file)
    prep_splits(pg_list, '/tmp/splits', 'nervous_system_a')






