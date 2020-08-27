import spacy
import utils


def test_table_detect():
    text = '''
Table 1. Univariate generalized linear regression analysis of sociodemographic predictors of COVID-19
infection by state.

'''
    text = '''
Table 1: Putative amino acid mutation signatures, their weight across genome corpus and closest literature citing the

'''
    lines = text.split('\n')
    out = utils.is_table_heading(lines[1], lines[0], lines[2])
    print('out:', str(out))


def test_table_end(nlp):
    text = '''
Mutation signature (LDA derived) (cu Wative Reference
'''
    text = '''
10. |ORF8-L84S, ORF1la-F3071Y, ORF14-Q44*, N-S197L, ORF3a-G196V 1507 [22]
'''
    lines = text.split('\n')
    import pdb; pdb.set_trace()
    x = utils.is_par_start(lines[1], 80, nlp)
    print(x)


def test_is_heading(nlp):
    text = '''
10. |ORF8-L84S, ORF1la-F3071Y, ORF14-Q44*, N-S197L, ORF3a-G196V 1507 [22]
'''
    lines = text.split('\n')
    import pdb; pdb.set_trace()
    x = utils.is_heading(lines[1], nlp)
    print(x)


def test_can_line_be_ignored():
    line = ' Rin  exp Rin '
    line = 'P work   out   ( psymptomatic'
    # import pdb; pdb.set_trace()
    x = utils.can_line_be_ignored(line, 80)
    print(x)


def test_is_mostly_numbers():
    line = '(87.0-94.5))'
    x = utils.is_mostly_numbers(line)
    print(x)


nlp = spacy.load("en_core_web_sm")
print("loaded spacy.")

# test_table_detect()

# test_table_end(nlp)
# test_is_heading(nlp)
# test_can_line_be_ignored()
test_is_mostly_numbers()

