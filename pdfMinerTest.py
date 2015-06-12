from pdfminer.pdfparser import PDFParser
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfinterp import PDFResourceManager
from pdfminer.pdfinterp import PDFPageInterpreter
from pdfminer.converter import PDFPageAggregator
from SegmentedPage import *
import codecs
import sys
from subprocess import check_call, CalledProcessError
from os.path import isfile, splitext, isdir
import Image
from os import listdir
from Segment import find_most_frequent_item
from xmlParser import XML_Parser

#Required packages pdfMiner, ImageMagick


SEGMENT_TITLE = "TITLE"
SEGMENT_AUTHORS = "AUTHORS"
SEGMENT_SECTION_TITLE = "SECTION TITLE"
SEGMENT_SECTION_BODY = "SECTION BODY"
SEGMENT_FOOTNOTE = "FOOTNOTE"
SEGMENT_OTHER = "OTHER"

class Article:

    def __init__(self, pages):
        self.pages = pages
        self.default_font = ""
        self.default_size = 0
        self.title = 0
        self.authors = 0

    def find_default_fonts(self):
        page_font_count = dict()
        size_count = dict()
        for page in self.pages:
            for segment in page.segments:
                if isinstance(segment, LTTextLine):
                    for k, v in segment.font_count.items():
                        if k in page_font_count:
                            page_font_count[k] += v
                        else:
                            page_font_count[k] = v
                    if segment.font_size in size_count:
                        size_count[segment.font_size] += segment.font_count[segment.font]
                    else:
                        size_count[segment.font_size] = segment.font_count[segment.font]

        self.default_font = find_most_frequent_item(page_font_count)
        self.default_size = find_most_frequent_item(size_count)


    def save_content(self):
        f = codecs.open(self.title.__str__()+".txt", "w", "utf-8")
        f.write("TITLE: " + self.title.__str__())
        f.write("AUTHORS: " + self.authors.__str__())
        for page in self.pages:
            for segment in page.segments:
                f.write(segment.__str__() + "\n")
            f.write("******************************************\n\n")
        f.close()

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
        page.concatenate_top_neighbor()
        pages.append( page )
        page_count += 1


    fp.close()

    pdfArticle = Article(pages)
    pdfArticle.find_default_fonts()

    if xml_file != "":
        XML_Parser.parse_file(xml_file)
        for page in pages:
            for segment in page.segments:
                tag = XML_Parser._find_tag_for_text(segment.text())
                segment.tag = tag
            page.save_line("./"+pdf_name+"_lines/")
            page.save_segments("./"+pdf_name+"_segments/")







