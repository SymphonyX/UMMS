import codecs
from Segment import find_most_frequent_item
from pdfminer.layout import *
from SegmentedPage import Page
import numpy as np
from xmlParser import XML_Parser

import matplotlib.pyplot as plt

class Article:

    def __init__(self, pages, name):
        self.name = name
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

    def find_content_distances(self):
        self.stats_dict = dict()
        for page in self.pages:
            for segment in page.segments:
                if segment.top_neighbor is not None and segment.font_size > 0 and segment.font_family == segment.top_neighbor.font_family and segment.font_size == segment.top_neighbor.font_size:
                    key = segment.key_for_font()
                    distance = Page.distance( (0, segment.top_center()[1]), (0, segment.bottom_center()[1]) )
                    if key not in self.stats_dict:
                        self.stats_dict[key] = [ distance ]
                    else:
                        self.stats_dict[key].append( distance )

    def concatenate_segments(self):
        for page in self.pages:
            page.concatenate_segments(self.stats_dict)

    def save_content(self, xml_file="", style="lines"):
        if style == "lines":
            for page in self.pages:
                page.save_line("./"+self.name+"_lines/")
        elif style == "segments":
            if xml_file != "":
                XML_Parser.parse_file(xml_file)
            for page in self.pages:
                for segment in page.segments:
                    tag = "" if xml_file == "" else XML_Parser._find_tag_for_text(segment.text())
                    segment.tag = tag
                page.save_segments("./"+self.name+"_segments/")

    def plot_stats(self):
        num, labels, values, errors, num_lines = [], [], [], [], []
        count = 1
        for k, v in self.stats_dict.items():
            errors.append( np.max(v) - np.min(v) )
            num_lines.append( len(v) )
            labels.append(k)
            values.append( np.mean(v) )
            num.append( count )
            count += 1

        plt.errorbar(num, values, xerr=0.0, yerr=errors)
        plt.plot(num, num_lines)
        plt.xticks(num, labels)
        plt.show()




