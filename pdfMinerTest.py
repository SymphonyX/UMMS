from pdfminer.pdfparser import PDFParser
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfinterp import PDFResourceManager
from pdfminer.pdfinterp import PDFPageInterpreter
from pdfminer.converter import PDFPageAggregator
from SegmentedPage import *

import sys
from subprocess import check_call, CalledProcessError
from os.path import isfile, splitext, isdir
import Image
from os import listdir
from Article import Article
#Required packages pdfMiner, ImageMagick


SEGMENT_TITLE = "TITLE"
SEGMENT_AUTHORS = "AUTHORS"
SEGMENT_SECTION_TITLE = "SECTION TITLE"
SEGMENT_SECTION_BODY = "SECTION BODY"
SEGMENT_FOOTNOTE = "FOOTNOTE"
SEGMENT_OTHER = "OTHER"


def convert(pdf):
    '''Convert a PDF to JPG'''
    if not isfile(pdf):
        print("ERROR", "Can't find {0}".format(pdf))
        return

    jpg = splitext(pdf)[0] + ".jpg"
    name = jpg.split("/")[-1]


    check_call(["mkdir", "tmp"])
    try:
        check_call(["convert", "-quality", "100%", pdf, "tmp/"+name])
        print("Converted", "{0} converted".format(pdf))
    except (OSError, CalledProcessError) as e:
        print("ERROR", "ERROR: {0}".format(e))

    files = listdir("./tmp")
    images = [None] * len(files)
    for f in files:
        position = int(f.split(".jpg")[0].split("-")[-1])
        image = Image.open("./tmp/"+f)
        images[position] = image

    check_call(["rm", "-R", "tmp"])
    return images



if __name__ == "__main__":

    file_name = sys.argv[1]
    xml_file = sys.argv[2] if len(sys.argv) > 2 else ""
    fp = open(file_name, "rb")

    parser = PDFParser(fp)
    document = PDFDocument(parser, "")

    rsrcmgr = PDFResourceManager()
    laparams = LAParams()
    device = PDFPageAggregator(rsrcmgr, laparams=laparams)

    interpreter = PDFPageInterpreter(rsrcmgr, device)

    page_images = convert(file_name)

    pdf_name = file_name.split(".pdf")[0].split("/")[-1]

    if isdir(pdf_name+"_lines"):
        check_call(["rm", "-R", pdf_name+"_lines"])
    check_call(["mkdir", pdf_name+"_lines"])

    if isdir(pdf_name+"_segments"):
        check_call(["rm", "-R", pdf_name+"_segments"])
    check_call(["mkdir", pdf_name+"_segments"])


    pages = list()
    page_count = 0
    for pdf_page in PDFPage.create_pages(document):
        interpreter.process_page(pdf_page)
        layout = device.get_result()
        page = Page(layout, page_number=page_count+1, jpg=page_images[page_count])
        page.find_segment_top_neighbors()
        pages.append( page )
        page_count += 1


    fp.close()

    pdfArticle = Article(pages, pdf_name)
    pdfArticle.find_default_fonts()
    pdfArticle.find_content_distances()
    pdfArticle.concatenate_segments()
    pdfArticle.save_content(xml_file)
    pdfArticle.plot_stats()









