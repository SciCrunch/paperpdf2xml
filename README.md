# paperpdf2xml

A set of Python 3 CLI to convert scientific papers in PDF format to  XML documents with sections and tables. 

## Prerequisites

* Make sure you have installed `pdftottext` utility installed for initial PDF to text conversion.

For Ubuntu/Debian
```
sudo apt-get install poppler-utils
```

For  RedHat/RHEL/ Fedora/ CentOS Linux
```
sudo yum install poppler-utils
```

* Install `spacy` NLP library and models (A virtual environment is recommended)

```bash
pip install spacy
python -m spacy download en_core_web_sm
```

## Usage

```
pdftotext paper.pdf paper.txt
python pdftext2pages.py -i paper.txt -o /tmp/paper1
python paper2xml.py -i /tmp/paper1/pdf.xml -o /tmp/paper1/paper.xml
```

The generated `tmp/paper1/paper.xml` contains paper section and table information with the common page headers and footers (line numbers) removed,
formula lines detected heuristically and stripped. The generated XML can then be used for text mining applications.


```bash
python pdftext2pages.py -h 

usage: pdftext2pages.py [-h] -i I -o O

optional arguments:
  -h, --help  show this help message and exit
  -i I        input PDF Text file
  -o O        output directory
```
  
```bash
python paper2xml.py -h
usage: paper2xml.py [-h] -i I -o O

optional arguments:
  -h, --help  show this help message and exit
  -i I        input PDF XML file
  -o O        output XML file


```

