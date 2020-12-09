import argparse
import spacy
import keras
from keras.models import Sequential
from keras.layers import Dense, Dropout, Flatten
from keras.layers import LSTM
from keras.models import Model

import numpy as np
from xml.etree.ElementTree import Element, SubElement
import xml.etree.ElementTree as ET
from os.path import expanduser

from glove_handler import GloveHandler
import utils


class Section(object):
    def __init__(self, sec_type, lines, prev_line, next_line):
        self.sec_type = sec_type
        self.lines = lines
        self.prev_line = prev_line
        self.next_line  = next_line

    def size(self):
        return len(self.lines)

    def get_context_window(self, line_idx, nlp):
        assert line_idx >= 0 and line_idx < self.size()
        tokens = []
        window = []
        has_last = True
        i = line_idx
        if i == 0:
            if self.prev_line:
                window.append(self.prev_line)
            else:
                tokens.append('\n')
            window.append(self.lines[i])
            if i+1 == self.size():
                if self.next_line:
                    window.append(self.next_line)
                else:
                    has_last = False
            else:
                window.append(self.lines[i+1])
        elif i+1 == self.size():
            if i == 0:
                if self.prev_line:
                    window.append(self.lines[i-1])
                else:
                    tokens.append('\n')
            else:
                window.append(self.lines[i-1])
            window.append(self.lines[i])
            if self.next_line:
                window.append(self.next_line)
            else:
                has_last = False
        else:
            window.append(self.lines[i-1])
            window.append(self.lines[i])
            window.append(self.lines[i+1])

        for doc in nlp.pipe(window, disable=['ner', 'parser']):
            for token in doc:
                tokens.append(token.text)
        if not has_last:
            tokens.append('\n')
        return tokens


def extract_sections(xml_file):
    page_sections = {}
    training_sections = []
    tree = ET.parse(xml_file)
    count = 0
    for node in tree.findall('.//page'):
        sections = []
        handle_page(node, sections)
        print("# of sections: {}".format(len(sections)))
        if has_bad_sections(sections):
            training_sections.extend(sections)
        page_sections[count] = sections
        count +=1
    return training_sections


def extract_page_sections(xml_file):
    page_sections = {}
    tree = ET.parse(xml_file)
    count = 0
    for node in tree.findall('.//page'):
        sections = []
        handle_page(node, sections)
        page_sections[count] = sections
        count +=1
    return page_sections


def has_bad_sections(sections):
    for section in sections:
        if section.sec_type == 'bad':
            return True
    return False


def handle_page(node, sections):
   lines = node.text.split("\n")
   print(len(lines))
   num_lines = len(lines)
   offset = 0
   i = 0
   while i < num_lines:
       line = lines[i]
       if  line.startswith('{junk}'):
           prev_line = lines[i-1] if i > 0 else None
           if i > 0:
               sections.append(create_before_section(i, offset, lines,
                           'good'))
           j = i
           while True:
               if lines[j].endswith('{junk}'):
                   j += 1
                   break
               elif j+1 >= num_lines:
                   break
               j += 1
           next_line = lines[j] if j < num_lines else None
           body = [l.replace('{junk}','') for l in  lines[i:j]]
           section = Section('bad', body, prev_line, next_line)
           sections.append(section)
           offset = j
           i = offset
       i += 1

   if offset < num_lines:
       prev_line = lines[offset-1] if offset > 0 else None
       section = Section("good", lines[offset:num_lines], prev_line, None)
       sections.append(section)


def create_before_section(i, offset, lines, sec_type):
    prev_line = lines[offset-1] if offset > 0 else None
    next_line = lines[i] if i < len(lines) else None
    return Section(sec_type, lines[offset:i], prev_line, next_line)


def prepare_section_tr_data(training_sections, nlp, max_length):
    data, labels = [], []
    for section in training_sections:
        num_lines = section.size()
        label  = 1 if section.sec_type == 'good' else 0
        for i in range(num_lines):
            instance = section.get_context_window(i, nlp)
            if len(instance) > max_length:
                instance = instance[0:max_length]
            data.append(instance)
            labels.append(label)
    return data, np.array(labels)


def prep_data(data, max_length, glove_handler, gv_dim=100):
    Xs = np.zeros((len(data), max_length * gv_dim), dtype='float32')
    for i, tokens in enumerate(data):
        for j, token in enumerate(tokens):
            offset = j * gv_dim
            vec = glove_handler.get_glove_vec(token)
            if vec:
                Xs[i, offset:offset+gv_dim] = vec
            else:
                vec = glove_handler.get_glove_vec('unk1')
                Xs[i, offset:offset+gv_dim] = vec
    return Xs

def build_LSTM_model(gv_dim=100, max_length=100):
    model = Sequential()
    model.add(LSTM(20, dropout=0.1,
                   recurrent_dropout=0.1,
                   return_sequences=False,
                   input_shape=(max_length, gv_dim)))
    model.add(Flatten())
    model.add(Dense(1, activation='sigmoid'))
    model.summary()
    model.compile(loss="binary_crossentropy", optimizer="rmsprop",
                  metrics=['acc'])
    return model


def train_model(train_X, train_labels, max_length=100, gv_dim=100):
    train_X = train_X.reshape(len(train_labels), max_length, gv_dim)
    model = build_LSTM_model(max_length=max_length)
    result = model.fit(train_X, train_labels, epochs=20, batch_size=32,
                       validation_split=0.1)
    print(result.history)


def train_model_full(train_X, train_labels, model_file, max_length=100, gv_dim=100):
    train_X = train_X.reshape(len(train_labels), max_length, gv_dim)
    model = build_LSTM_model(max_length=max_length)
    result = model.fit(train_X, train_labels, epochs=20, batch_size=32)
    print(result.history)
    model.save(model_file)
    print("saved model:", model_file)


def train(data, labels, max_length, glove_handler, gv_dim=100):
    Xs = prep_data(data, max_length, glove_handler, gv_dim=gv_dim)
    train_model(Xs, labels, max_length=max_length, gv_dim=gv_dim)


def train_full(data, labels, max_length, glove_handler, model_file, gv_dim=100):
    Xs = prep_data(data, max_length, glove_handler, gv_dim=gv_dim)
    train_model_full(Xs, labels, model_file, max_length=max_length, gv_dim=gv_dim)


def filter(xml_file, nlp, glove_handler, out_xml_file,
        model_file='junk_remover_model.h5', threshold = 0.5):
    max_length = 100
    gv_dim = 100
    #model = build_LSTM_model(max_length=max_length)
    #model.load('junk_remover_model.h5')
    model = keras.models.load_model(model_file)
    # model._make_predict_function()
    page_sections = extract_page_sections(xml_file)
    top = Element('pdf')
    for page_idx, sections in page_sections.items():
        assert len(sections) == 1
        data, labels = prepare_section_tr_data(sections, nlp, max_length)
        pred_X = prep_data(data, max_length, glove_handler, gv_dim=gv_dim)
        pred_X = pred_X.reshape(len(labels), max_length, gv_dim)
        y_preds = model.predict(pred_X)
        lines = sections[0].lines
        content = ""
        for i, ypred in enumerate(y_preds):
            if ypred > threshold:
                print(lines[i])
                content += lines[i] + "\n"
        page_el = SubElement(top, 'page')
        page_el.text = content
        print('-'*80)

    utils.indent(top)
    out_tree = ET.ElementTree(top)
    out_tree.write(out_xml_file, encoding="UTF-8")
    print("wrote file:", out_xml_file)
    print('done.')


def usage(parser):
    import sys
    parser.print_help(sys.stderr)
    sys.exit(1)


def main():
    desc = '''
    This tool learns what is considered as junk in text extracted
    from textbooks/articles in PDF format to cleanup `hocr2pages.py`
    generated XML files.
    '''
    parser = argparse.ArgumentParser(description=desc)
    parser.add_argument('-c', action='store', help="one of train or clean",
            required=True)
    parser.add_argument('-i', action='store', help="input XML file", required=True)
    parser.add_argument('-o', action='store', help="cleaned XML file (in clean mode)")
    parser.add_argument('-m', action='store', help="classifier model file")
    args = parser.parse_args()

    cmd = args.c
    if cmd != 'train' and cmd != 'clean':
        usage(parser)

    in_file = args.i

    home = expanduser("~")
    db_file = home + "/medline_glove_v2.db"
    model_file = args.m if args.m else 'junk_remover_model.h5'

    nlp = spacy.load("en_core_web_sm")
    print("loaded spacy.")
    glove_handler = GloveHandler(db_file)
    max_length= 100

    if cmd == 'train':
        training_sections = extract_sections(in_file)
        data, labels = prepare_section_tr_data(training_sections, nlp, max_length)
        train_full(data, labels, max_length, glove_handler, model_file)
    else:
        if not args.o:
            usage(parser)
        out_xml_file = args.o
        filter(in_file, nlp, glove_handler, out_xml_file, model_file=model_file)


def test_driver():
    home = expanduser("~")
    db_file = home + "/medline_glove_v2.db"
    # extract_sections('3_Cholinergic_Receptors.xml')
    training_sections = extract_sections('SECTION_VI_THE_URINARY_SYSTEM.xml')
    nlp = spacy.load("en_core_web_sm")
    print("loaded spacy.")
    glove_handler = GloveHandler(db_file)
    max_length= 100
    # data, labels = prepare_section_tr_data(training_sections, nlp, max_length)
    # train_full(data, labels, 'junk_remover_model.h5',  max_length, glove_handler)
    filter('SECTION_V_THE_RESPIRATORY_SYSTEM.xml', nlp, glove_handler,
           '/tmp/x.xml')


if __name__ == '__main__':
    main()


