import re
import unicodedata

'''
copy and paste from http://effbot.org/zone/element-lib.htm#prettyprint
it basically walks your tree and adds spaces and newlines so the tree is
printed in a nice way
'''


def indent(elem, level=0):
    i = "\n" + level*"  "
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + "  "
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
        for elem in elem:
            indent(elem, level+1)
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i


def isempty(line):
    return not line.strip()


def is_table_heading(line, prev_line, next_line):
    pat = re.compile(r'(^s*Table\s+\d+[\.:]?\s+)[A-Z]')
    m = pat.match(line)
    if m:
        prefix = m.group(1)
        heading = line.replace(prefix, '').strip()
        if not next_line or isempty(next_line):
            return (heading, False)
        else:
            heading += ' ' + next_line
            return (heading, True)

    return None


def can_follow_verb(token):
    tag = token.tag_
    return tag.startswith('NN') or tag.startswith('DT') or tag.startswith('IN') or tag.startswith('MD')


def is_mostly_numbers(line):
    num_spans = []
    for m in re.finditer(r'-?\d+(\.\d+)?', line):
        num_spans.append((m.start(), m.end()))
    if len(num_spans) > 0:
        rem = line
        for ns in num_spans:
            number = line[ns[0]:ns[1]]
            rem = rem.replace(number, '')
        rem = re.sub(r'[\(\)\[\]]', '', rem)
        rem_ratio = len(rem) / float(len(line))
        if rem_ratio <= 0.15:
            return True
    return False


def is_figure_text(line_toks, nlp):
    if len(line_toks) >= 5:
        return False
    has_title_case = False
    has_verb  = False
    num_nouns = 0
    has_period = False
    line = " ".join(line_toks)
    if is_mostly_numbers(line):
        return True
    for doc in nlp.pipe([line], disable=['ner', 'parser']):
        num_tokens = len(doc)
        for i, token in enumerate(doc):
            if token.text == '.':
                has_period = True
            m = re.match(r'^X[x]+$', token.shape_)
            if i == 0 and m:
                has_title_case = True
            if token.tag_.startswith('VB'):
                has_verb = True
            if token.tag_.startswith('NN'):
                num_nouns += 1

    noun_frac = num_nouns / float(num_tokens) if num_tokens > 0 else 0
    if not has_verb and not has_period and noun_frac >= 0.5:
        return True
    return False



def is_heading(line, nlp):
    if isempty(line):
        return (False, False)
    all_capitals = True
    has_verb = False
    all_alpha = True
    num_nouns = 0
    has_period = False
    has_title_case = False
    has_sec_num = False
    # num_tokens = 0
    sec_num_pat = re.compile(r'(^\s*\d+\.[\d+.]*\s)')
    alpha_sec_pat = re.compile(r'(\^[abcdefg]\.\s*)')
    headings_set = {"abstract", "introduction", "background", "methods",
                    "materials and methods", "discussion", "conclusions",
                    "references", "acknowledgements", "online methods",
                    "bibliography"}
    m = sec_num_pat.match(line)
    if m:
        prefix = m.group(1)
        has_sec_num = True
        line = line.replace(prefix, '').strip()
    else:
        m = alpha_sec_pat.match(line)
        if m:
            prefix = m.group(1)
            has_sec_num = True
            line = line.replace(prefix, '').strip()
    ll = line.strip().lower()
    # handle cases like 'Methods:'
    if ll.endswith(':'):
        ll = ll[:len(ll)-1]

    if ll in headings_set:
        return (True, True)

    if is_mostly_numbers(line):
        return False, False

    for doc in nlp.pipe([line], disable=['ner', 'parser']):
        num_tokens = len(doc)
        for i, token in enumerate(doc):
            if token.text == '.':
                has_period = True
            m = re.match(r'^X[X\.]+$', token.shape_)
            if not m:
                all_capitals = False
            m = re.match(r'^X[x]+$', token.shape_)
            if i == 0 and m:
                has_title_case = True
            if not token.is_alpha:
                all_alpha = False
            if token.tag_.startswith('VB'):
                has_verb = True
            if token.tag_.startswith('NN'):
                num_nouns += 1
    # if has_verb:
    #     print("-- ", line)
    noun_frac = num_nouns / float(num_tokens)
    if has_sec_num and not has_verb:
        return (True, False)

    if all_capitals and not has_verb:
        return (True, False)
    if all_alpha and has_title_case and not has_verb and noun_frac > 0.5:
        return (True, False)
    if has_title_case and not has_verb and num_nouns > 0 and noun_frac > 0.5 and not has_period:
        return (True, False)
    return (False, False)


def is_par_start(line, median_sent_len, nlp):
    if isempty(line):
        return False
    short_line = len(line) < int(0.5 * median_sent_len)
    has_verb = False
    num_nouns = 0
    for doc in nlp.pipe([line]):
        verb_idx = -1
        no_toks = len(doc)
        for i, token in enumerate(doc):
            if token.tag_.startswith('VB'):
                has_verb = True
                verb_idx = i
            if verb_idx > 0 and i == verb_idx+1 and not can_follow_verb(token):
                has_verb = False
            if token.tag_.startswith('NN'):
                num_nouns += 1
    if has_verb and (verb_idx == 0 or verb_idx+1 == no_toks):
        has_verb = False
    if not has_verb:
        return False
    if short_line and not has_verb:
        return False
    return True


def get_ascii_ratio(line):
    t = unicodedata.normalize('NFD', line)
    tot_chars = 0
    tot_ascii = 0
    for c in t:
        if c != ' ':
            if ord(c) < 128:
                tot_ascii += 1
            tot_chars += 1
    return tot_ascii / float(tot_chars + 0.000001)


def can_line_be_ignored(line, median_sent_len):
    if isempty(line):
        return False
    if len(line) < 3:
        return True
    if len(line) < 5:
        if line.isnumeric():
            return True
        elif re.search(r'\(\d+\)', line):
            return True
    ratio = get_ascii_ratio(line)
    if median_sent_len > 40:
        if len(line) < median_sent_len/2:
            if ratio < 0.85:
                return True
    elif ratio < 0.85:
        return True
    return False


def get_perf_results(true_labels, preds):
    """Calculates P, R, F1 both for good and bad labels"""
    n_bad_correct, n_bad_predicted, n_bad_gold = 0, 0, 0
    n_good_correct, n_good_predicted, n_good_gold = 0, 0, 0
    for y_true, pred in zip(true_labels, preds):
        if y_true == 1:
            n_good_gold += 1
            if pred == 1:
                n_good_predicted += 1
                if pred == y_true:
                    n_good_correct += 1
            else:
                n_bad_predicted += 1
        else:
            n_bad_gold += 1
            if pred == 0:
                n_bad_predicted += 1
                if pred == y_true:
                    n_bad_correct += 1
            else:
                n_good_predicted += 1
    if n_good_correct == 0:
        p_good, r_good, f1_good = 0, 0, 0
    else:
        p_good = 100.0 * n_good_correct / n_good_predicted
        r_good = 100.0 * n_good_correct / n_good_gold
        f1_good = 2 * p_good * r_good / (p_good + r_good)

    if n_bad_correct == 0:
        p_bad, r_bad, f1_bad = 0, 0, 0
    else:
        p_bad = 100.0 * n_bad_correct / n_bad_predicted
        r_bad = 100.0 * n_bad_correct / n_bad_gold
        f1_bad = 2 * p_bad * r_bad / (p_bad + r_bad)

    return {'p_good': p_good, 'r_good': r_good,
            'f1_good': f1_good, 'p_bad': p_bad,
            'r_bad': r_bad, 'f1_bad': f1_bad}
