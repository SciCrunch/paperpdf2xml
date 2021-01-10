from xml.etree.ElementTree import Element, SubElement
import xml.etree.ElementTree as ET
import os.path
from os.path import join
import spacy

import utils
import numpy as np
from junk_remover import extract_page_sections
from junk_remover import extract_sections, prepare_section_tr_data, train_full
from junk_remover import evaluate
from glove_handler import GloveHandler


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


def train_test_splits(out_dir, prefix, result_file):
    import glob
    home = os.path.expanduser("~")
    db_file = home + "/pmd_2021_01_abstracts_glove.db"
    nlp = spacy.load("en_core_web_sm")
    print("loaded spacy.")
    glove_handler = GloveHandler(db_file)
    max_length = 100
    models_dir = join(out_dir, 'models')
    if not os.path.exists(models_dir):
        os.makedirs(models_dir)

    with open(result_file, 'w') as f:
        for i in range(1, 10):
            tr_file = glob.glob(out_dir + '/*train_' + str(i) + '[0-9].xml')[0]
            tst_file = glob.glob(out_dir + '/*test_' + str(i) + '[0-9].xml')[0]
            print(tr_file, tst_file)
            split_perc = tr_file.split('.')[-2][-2:]
            model_file = join(models_dir, 'split_model_' + split_perc + ".h5")
            print(model_file)
            comp = 100 - int(split_perc)
            f.write("{}/{} split\n".format(split_perc, str(comp)))
            training_sections = extract_sections(tr_file)
            data, labels = prepare_section_tr_data(training_sections, nlp,
                                                   max_length)
            train_full(data, labels, max_length, glove_handler, model_file)
            # evaluate
            r = evaluate(tst_file, nlp, glove_handler, model_file=model_file)
            print(f"Good P:{r['p_good']:.2f} R:{r['r_good']:.2f} F1:{r['f1_good']:.2f}", file=f)
            print(f"Bad  P:{r['p_bad']:.2f} R:{r['r_bad']:.2f} F1:{r['f1_bad']:.2f}", file=f)





if __name__ == '__main__':
    # in_file = 'data/annotations/Unit_IX_The_Nervous_System_A.xml'
    # pg_list = prep_page_stats(in_file)
    # prep_splits(pg_list, '/tmp/splits', 'nervous_system_a')
    train_test_splits('/tmp/splits', 'nervous_system_a',
                      "full_seq_model_results.txt")

