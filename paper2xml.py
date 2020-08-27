import re
import numpy as np
import argparse
from xml.etree.ElementTree import Element, SubElement
import xml.etree.ElementTree as ET
import spacy
import utils


def isempty(line):
    return not line.strip()


def is_same(text1, text2):
    if text1 == text2:
        return True
    text1 = re.sub(r'\s+', '', text1)
    text2 = re.sub(r'\s+', '', text2)
    return text1 == text2


class Table:
    def __init__(self, title):
        self.title = title
        self.body = ''

    def add_2body(self, body):
        self.body += body

    def to_xml(self, top):
        sect_el = SubElement(top, 'table')
        title_el = SubElement(sect_el, 'title')
        title_el.text = self.title
        if self.body:
            body_el = SubElement(sect_el, 'body')
            body_el.text = self.body


class Section:
    def __init__(self, title):
        self.title = title
        self.body = ''
        self.tables = []

    def add_2body(self, body):
        self.body += body

    def add_table(self, table: Table):
        self.tables.append(table)

    def to_xml(self, top):
        sect_el = SubElement(top, 'section')
        title_el = SubElement(sect_el, 'title')
        title_el.text = self.title
        if self.body:
            body_el = SubElement(sect_el, 'body')
            body_el.text = self.body
        if self.tables:
            for table in self.tables:
                table.to_xml(sect_el)


class Page:
    def __init__(self, page_id):
        self.page_id = page_id
        self.lines = None
        self.median_sent_len = None
        self.header_indices = []
        self.headings_detected = False

    def extract_lines(self, text):
        self.lines = text.split('\n')
        cleaned = []
        line_no_count = 0
        for line in self.lines:
            line = line.replace('\f', '')
            m = re.search(r'^\d+ ', line)
            if m:
                line_no_count += 1
            cleaned.append(line)
        # import pdb; pdb.set_trace()
        fraction = line_no_count / float(len(self.lines))
        if fraction >= 0.5:
            self.lines = []
            for line in cleaned:
                m = re.search(r'^\d+ ', line)
                if m:
                    line = re.sub(r'^\d+ ', '', line)
                    self.lines.append(line)
                elif isempty(line):
                    self.lines.append(line)
        else:
            self.lines = cleaned

        sl = [len(line) for line in self.lines if len(line.strip()) > 0]
        print(sl)
        self.median_sent_len = np.median(sl)

    def to_text(self):
        cleaned = []
        line_no_count = 0
        for line in self.lines:
            line = line.strip()
            line = line.replace('\f', '')
            m = re.search(r'^\d+ ', line)
            if m:
                line_no_count += 1
            cleaned.append(line)
        fraction = line_no_count / float(len(self.lines))
        if fraction >= 0.5:
            self.lines = []
            for line in cleaned:
                m = re.search(r'^\d+ ', line)
                if m:
                    line = re.sub(r'^\d+ ', '', line)
                    self.lines.append(line)
        else:
            self.lines = cleaned
        return "\n".join(self.lines)

    def __len__(self):
        return len(self.lines)

    def get_median_sent_len(self):
        return self.median_sent_len

    def get_header_candidate(self):
        hl = []
        for line in self.lines:
            if not line.strip():
                break
            else:
                hl.append(line.strip())
        return " ".join(hl)

    def strip_header(self):
        idx = -1
        for i, line in enumerate(self.lines):
            if not line.strip():
                idx = i
                break
        if idx > 0:
            self.lines = self.lines[idx:]

    def _is_eligible_heading(self, line, i, num_lines, msl, nlp):
        ok, known_title = utils.is_heading(line, nlp)
        if known_title:
            return True
        if ok and i+1 < num_lines:
            if isempty(self.lines[i+1]):
                return True
            if utils.is_par_start(self.lines[i+1], msl, nlp):
                return True
        return False

    def detect_headings(self, nlp):
        if self.headings_detected:
            return
        num_lines = len(self.lines)
        prev_header = False
        msl = self.median_sent_len
        for i, line in enumerate(self.lines):
            if prev_header:
                prev_header = False
                if isempty(line):
                    continue
            if i == 0:
                if i+1 < num_lines:
                    if self._is_eligible_heading(line, i, num_lines, msl, nlp):
                        self.header_indices.append(i)
                        prev_header = True
            else:
                if isempty(self.lines[i-1]):
                    if self._is_eligible_heading(line, i, num_lines, msl, nlp):
                        self.header_indices.append(i)
                        prev_header = True
                else:
                    if self._is_eligible_heading(line, i, num_lines, msl, nlp):
                        self.header_indices.append(i)
                        prev_header = True

        print(self.header_indices)
        self.headings_detected = True

    def get_lines(self):
        lt_list = []
        idx = 0
        size = len(self.header_indices)
        for i, line in enumerate(self.lines):
            if idx < size and i == self.header_indices[idx]:
                lt_list.append((line, True))
                idx += 1
            else:
                lt_list.append((line, False))
        return lt_list

    def __str__(self):
        s = ""
        idx = 0
        for i, line in enumerate(self.lines):
            if idx < len(self.header_indices) and i == self.header_indices[idx]:
                s += '>>>> '
                idx += 1
            s += line.strip() + '\n'
        return s


class Doc:
    def __init__(self):
        self.pages = []
        self.sections = []

    def add_page(self, page: Page):
        self.pages.append(page)

    def __len__(self):
        return len(self.pages)

    def _remove_footers(self):
        pat = re.compile(r'^\s*\d+\s*$')
        for page in self.pages:
            idx = -1
            for i, line in enumerate(reversed(page.lines)):
                if isempty(line):
                    idx = i + 1
                else:
                    m = pat.match(line)
                    if m:
                        idx = i + 1
                    else:
                        break
            if idx > 0:
                page.lines = page.lines[:-idx]

    def _remove_headers(self):
        # import pdb; pdb.set_trace()
        header = ""
        for lidx in range(0, 10):
            ref_line = None
            same_count = 1
            for i, page in enumerate(self.pages):
                if i == 0:
                    if lidx < len(page):
                        ref_line = page.lines[lidx]
                else:
                    if ref_line and lidx < len(page):
                        line = page.lines[lidx]
                        if is_same(ref_line, line):
                            same_count += 1
            fraction = same_count / float(len(self.pages))
            if fraction >= 0.75:
                header += ref_line + ' '
            else:
                break
        header = header.strip()
        if header:
            print('>>> Header:', header)
            for page in self.pages:
                idx = -1
                for lidx in range(0, 10):
                    if lidx < len(page):
                        line = page.lines[lidx].strip()
                        if header.find(line) != -1:
                            idx = lidx
                        else:
                            break
                if idx >= 0:
                    page.lines = page.lines[idx+1:]

    def process(self, nlp):
        self._remove_headers()
        self._remove_footers()
        cur_section = None
        for page in self.pages:
            page.detect_headings(nlp)
            lt_list = [lt for lt in page.get_lines()]
            page_len = len(lt_list)
            in_table = False
            cur_table = None
            skip_next = False
            table_start_idx = -1
            msl = page.get_median_sent_len()
            for i, lt in enumerate(lt_list):
                line, is_heading = lt
                if skip_next:
                    skip_next = False
                    continue
                prev_line = lt_list[i-1][0] if i > 0 else None
                next_line = lt_list[i+1][0] if i+1 < page_len else None
                is_last_line = i+1 == page_len
                if not cur_section:
                    if is_heading:
                        cur_section = Section(line)
                        print('1 Section({})'.format(line))
                    else:
                        cur_section = Section('')
                    self.sections.append(cur_section)
                    cur_section.add_2body(line + '\n')
                    continue
                if is_heading and not in_table:
                    cur_section = Section(line)
                    print('2 Section({})'.format(line))
                    self.sections.append(cur_section)
                else:
                    if not in_table:
                        t = utils.is_table_heading(line, prev_line, next_line)
                        if t:
                            table_title = t[0]
                            skip_next = t[1]
                            cur_table = Table(table_title)
                            print('1 Table({})'.format(table_title))
                            cur_section.add_table(cur_table)
                            in_table = True
                            table_start_idx = i
                        else:
                            if not utils.can_line_be_ignored(line, msl):
                                cur_section.add_2body(line + '\n')
                    else:
                        if utils.is_par_start(line, msl, nlp):
                            if table_start_idx > 0 and i < table_start_idx + 5:
                                cur_table.add_2body(line + '\n')
                            else:
                                in_table = False
                                cur_table = None
                                table_start_idx = -1
                                if not utils.can_line_be_ignored(line, msl):
                                    cur_section.add_2body(line + '\n')
                        else:
                            if not utils.can_line_be_ignored(line, msl):
                                cur_table.add_2body(line + '\n')
                            if is_last_line:
                                in_table = False
                                cur_table = None

    def to_xml(self, out_file):
        top = Element('paper')
        for section in self.sections:
            section.to_xml(top)
        utils.indent(top)
        tree = ET.ElementTree(top)
        tree.write(out_file, encoding='utf-8')
        print("wrote file:", out_file)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', action='store', help="input PDF XML file", required=True)
    parser.add_argument('-o', action='store', help="output XML file", required=True)

    args = parser.parse_args()

    in_file = args.i
    out_file = args.o

    nlp = spacy.load("en_core_web_sm")
    print("loaded spacy.")

    tree = ET.parse(in_file)
    root = tree.getroot()

    doc = Doc()
    for i, child in enumerate(root):
        if not child.text:
            continue
        text = child.text
        page = Page(i+1)
        page.extract_lines(text)
        print('# of lines in page:{} median sentence length:{}'.format(
            len(page), page.get_median_sent_len()))
        doc.add_page(page)

    print('# of pages:{}'.format(len(doc)))
    doc.process(nlp)
    doc.to_xml(out_file)
