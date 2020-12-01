import spacy
from keras.models import Sequential
from keras.layers import Dense, Dropout, Flatten
from keras.layers import LSTM
from keras.models import Model

import numpy as np
from xml.etree.ElementTree import Element, SubElement
import xml.etree.ElementTree as ET

from glove_handler import GloveHandler


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
    sections = []
    tree = ET.parse(xml_file)
    for node in tree.findall('.//page'):
        handle_page(node, sections)
        print("# of sections: {}".format(len(sections)))
    return sections


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
               elif j+1 < num_lines:
                   break
               j += 1
           next_line = lines[j] if j < num_lines else None
           section = Section('bad', lines[i:j], prev_line, next_line)
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


def train_model(train_X, train_labels, max_length=100):
    model = build_LSTM_model(max_length=max_length)
    result = model.fit(train_X, train_labels, epochs=20, batch_size=32,
                       validation_split=0.1)
    print(result.history)



extract_sections('3_Cholinergic_Receptors.xml')
