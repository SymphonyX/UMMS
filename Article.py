import codecs
from Segment import find_most_frequent_item
from pdfminer.layout import *
from SegmentedPage import Page
import numpy as np
from xmlParser import XML_Parser
import math

import matplotlib.pyplot as plt

class Section:

    def __init__(self, title, segments):
        self.title = title
        self.segments = segments

class Article:

    def __init__(self, pages, name):
        self.name = name
        self.pages = pages
        self.default_font_family = ""
        self.default_font_type = ""
        self.default_size = 0
        self.title = "-"
        self.authors = "-"
        self.sections = list()
        self.column_dim = list()

    def find_default_fonts(self):
        page_font_count = dict()
        size_count = dict()
        for page in self.pages:
            for segment in page.segments:
                if segment.contains_text():
                    for k, v in segment.font_count.items():
                        if k in page_font_count:
                            page_font_count[k] += v
                        else:
                            page_font_count[k] = v

                    if segment.font_size in size_count:
                        size_count[segment.font_size] += segment.font_count[segment.font]
                    else:
                        size_count[segment.font_size] = segment.font_count[segment.font]


        font = find_most_frequent_item(page_font_count).split(",")
        self.default_font_family = font[0]
        self.default_font_type =  "Regular" if len(font) == 1 else font[1]
        self.default_size = find_most_frequent_item(size_count)


    def extract_text(self):
        f = codecs.open(self.title.__str__()+".txt", "w", "utf-8")
        for section in self.sections:
            f.write("Section Title: " + section.title)
            f.write("\n")
            for segment in section.segments:
                f.write(segment.text())
            f.write("\n*********************************************************\n")


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


    def identify_sections(self):

        current_section = list()
        segments_used = list()
        for page in reversed(self.pages):
            segments_bottom = sorted(page.segments, key=lambda seg: (seg.bbox[1], -seg.bbox[0]) )
            for segment in segments_bottom:
                for dim in self.column_dim:
                    if segment.font_size > self.default_size:
                        current_section = list(reversed(current_section))
                        section = Section(segment.text(), current_section)
                        if len(current_section) > 0:
                            self.sections.append(section)
                        current_section = list()

                    elif math.fabs(segment.bbox[0] - dim[0]) < 1.0 and segment not in segments_used:
                        segments_used.append(segment)

                        current_section.append(segment)

        self.sections = list(reversed(self.sections))


    def identify_columns(self):
        for page in self.pages:
            for segment in page.segments:
                if segment.font_family == self.default_font_family and math.fabs(segment.font_size - self.default_size) < 0.1:
                    column_dim_copy = list(self.column_dim)
                    updated_dim = False

                    for dim in column_dim_copy:
                        if math.fabs(segment.bbox[0] - dim[0]) < 1.0:
                            self.column_dim.remove(dim)
                            minx = segment.bbox[0] if segment.bbox[0] < dim[0] else dim[0]
                            maxx = segment.bbox[2] if segment.bbox[2] > dim[1] else dim[1]
                            self.column_dim.append( (minx, maxx) )
                            updated_dim = True
                            break

                    if updated_dim == False:
                        self.column_dim.append( (segment.bbox[0], segment.bbox[2]) )


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




