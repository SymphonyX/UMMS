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
from xmlParser import XML_Parser
import tkFileDialog
import tkMessageBox
import pickle
#Required packages pdfMiner, ImageMagick, PIL

import Tkinter

SEGMENT_TITLE = "TITLE"
SEGMENT_AUTHORS = "AUTHORS"
SEGMENT_SECTION_TITLE = "SECTION TITLE"
SEGMENT_SECTION_BODY = "SECTION BODY"
SEGMENT_FOOTNOTE = "FOOTNOTE"
SEGMENT_OTHER = "OTHER"


def label_assignment_gui(feature_vecs, pdfArticle):
    print "Starting GUI"
    window = Tkinter.Tk()
    window.resizable(width=False, height=False)
    window.geometry('{}x{}'.format(700, 600))


    tags_listbox = Tkinter.Listbox(window)
    tags_listbox.place(x=10, y=100, height=200, width=100)
    tagslist_scrollbar = Tkinter.Scrollbar(window)
    tagslist_scrollbar.place(x=110, y=100, height=200)
    tagslist_scrollbar.config(command=tags_listbox.yview)
    tags_listbox.config(yscrollcommand=tagslist_scrollbar.set)

    tags_usage = []
    for feature, tag in feature_vecs:
        tags_listbox.insert(Tkinter.END, tag)
        tags_usage.append(0)


    tags_textbox = Tkinter.Text(window)
    tags_textbox.place(x=130, y=100, height=200, width=500)
    tagstxt_scrollbar = Tkinter.Scrollbar(window)
    tagstxt_scrollbar.place(x=630, y=100, height=200)
    tagstxt_scrollbar.config(command=tags_textbox.yview)
    tags_textbox.config(yscrollcommand=tagstxt_scrollbar.set)

    global selected_tag_index
    selected_tag_index = 0
    tags_textbox.insert(Tkinter.END, feature_vecs[0][0].text)

    label_var = Tkinter.StringVar()
    tags_label = Tkinter.Label(window, textvariable=label_var)
    tags_label.place(x=10, y=80, height=20, width=100)

    def onselect(evt):
        w = evt.widget
        global selected_tag_index
        selected_tag_index = int(w.curselection()[0])
        print "Selected Tag Index: ", selected_tag_index
        tags_textbox.delete('1.0',Tkinter.END)
        tags_textbox.insert(Tkinter.END, feature_vecs[selected_tag_index][0].text)
        label_var.set("Count: " + str(tags_usage[selected_tag_index]))

    tags_listbox.bind('<<ListboxSelect>>', onselect)

    segment_listbox = Tkinter.Listbox(window)
    segment_listbox.place(x=10, y=350, height=200, width=100)
    segmentlist_scrollbar = Tkinter.Scrollbar(window)
    segmentlist_scrollbar.place(x=110, y=350, height=200)
    segmentlist_scrollbar.config(command=segment_listbox.yview)
    segment_listbox.config(yscrollcommand=segmentlist_scrollbar.set)
    count = 0
    all_segments = []
    for i, page in enumerate(pdfArticle.pages):
        for j, segment in enumerate(page.segments):
            segment_listbox.insert(Tkinter.END, "Segment " + str(count))
            all_segments.append( (segment, -1) )
            count += 1

    segment_textbox = Tkinter.Text(window)
    segment_textbox.place(x=130, y=350, height=200, width=500)
    segmenttxt_scrollbar = Tkinter.Scrollbar(window)
    segmenttxt_scrollbar.place(x=630, y=350, height=200)
    segmenttxt_scrollbar.config(command=segment_textbox.yview)
    segment_textbox.config(yscrollcommand=segmenttxt_scrollbar.set)

    segment_textbox.insert(Tkinter.END, all_segments[0][0])
    global index
    index = 0

    labelvar_segment = Tkinter.StringVar()
    segment_label = Tkinter.Label(window, textvariable=labelvar_segment)
    segment_label.place(x=10, y=320, height=20, width=100)

    def onsegmentselect(evt):
        w = evt.widget
        global index
        index = int(w.curselection()[0])
        print "Selected Segment Index: ", index
        segment_textbox.delete('1.0',Tkinter.END)
        segment_textbox.insert(Tkinter.END, all_segments[index][0].text())
        labelvar_segment.set(all_segments[index][0].tag)


    segment_listbox.bind('<<ListboxSelect>>', onsegmentselect)

    def button_assign_callback():
        global selected_tag_index
        global index
        tags_usage[selected_tag_index] += 1
        all_segments[index] = (all_segments[index][0], selected_tag_index)
        all_segments[index][0].tag = feature_vecs[selected_tag_index][1]

        label_var.set( "Count: " + str(tags_usage[selected_tag_index]) )
        labelvar_segment.set( all_segments[index][0].tag )

    def button_delete_callback():
        global index
        all_segments[index][0].tag = ""
        labelvar_segment.set( "" )
        if all_segments[index][1] != -1:
            tags_usage[all_segments[index][1]] -= 1
            label_var.set("Count: " + str(tags_usage[all_segments[index][1]]))
            all_segments[index] = (all_segments[index][0], -1)


    def button_save_callback():
        save_file = tkFileDialog.asksaveasfile()
        save_file = open(save_file.name, "w")
        data = [ pdfArticle.name, pdfArticle.pages, tags_usage, all_segments]
        pickle.dump(data, save_file)
        save_file.close()

    def button_load_callback():
        file_data = tkFileDialog.askopenfile()
        f = open(file_data.name, "r")
        data = pickle.load(f)
        global tags_usage
        pdfname = data[0]
        if pdfname != pdfArticle.name:
            tkMessageBox.showwarning("File Error", "The file you are trying to load does not belong to the processing pdf.")
        else:
            pages = data[1]
            tags_usage = data[2]
            global all_segments
            all_segments = data[3]
            pdfArticle.pages = pages


    button_assign = Tkinter.Button(window, text="Assign Tag", command=button_assign_callback).place(x=150, y=50, width=100, height=30)
    button_delete = Tkinter.Button(window, text="Delete Tag", command=button_delete_callback).place(x=150, y=320, width=100, height=30)
    button_save = Tkinter.Button(window, text="Save Tag File", command=button_save_callback).place(x=300, y=50, width=100, height=30)
    button_load = Tkinter.Button(window, text="Load Tag File", command=button_load_callback).place(x=400, y=50, width=100, height=30)


    window.mainloop()




def convert(pdf):
    '''Convert a PDF to JPG'''
    if not isfile(pdf):
        print("ERROR", "Can't find {0}".format(pdf))
        return

    jpg = splitext(pdf)[0] + ".jpg"
    name = jpg.split("/")[-1]

    if isdir("tmp"):
        check_call(["rm", "-R", "tmp"])
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

    if xml_file != "":
        label_mode = raw_input("> Select (A)utomatic or (M)anual label assignment: ")
        if label_mode == "M" or label_mode == "m":
            print "Manual label assignment selected"
        elif label_mode == "A" or label_mode == "a":
            print "Automatic label assignment selected"
        else:
            print "Unrecognized option, defaulting to automatic label assignment"
            label_mode = "A"

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

    image_folder = pdf_name+"_images"
    if isdir(image_folder):
        check_call(["rm", "-R", image_folder])
    check_call(["mkdir", image_folder])

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
    pdfArticle.save_content(style="lines")
    pdfArticle.concatenate_segments()
    pdfArticle.identify_num_columns()
    pdfArticle.identify_sections()
    pdfArticle.save_images(image_folder)

    if xml_file != "":
        if label_mode == "A" or label_mode == "a":
            pdfArticle.assign_labels(xml_file)
            pdfArticle.print_label_accuracy()
        else:
            feature_vecs = XML_Parser.retrieve_tags(xml_file)
            label_assignment_gui(feature_vecs, pdfArticle)

    pdfArticle.save_content(style="segments")
    #pdfArticle.extract_text()

    #pdfArticle.plot_stats()









