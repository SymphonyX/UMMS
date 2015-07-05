import codecs
from Segment import find_most_frequent_item
from pdfminer.layout import *
from SegmentedPage import Page
import numpy as np
from xmlParser import XML_Parser
import math
import os
import matplotlib.pyplot as plt
from binascii import b2a_hex

class Section:

    def __init__(self, title, segments):
        self.title = title
        self.segments = segments

    def text(self):
        txt = ""
        for segment in self.segments:
            txt += segment.text() + " "
        return txt

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
        self.num_columns = 0
        self.column_dim = list()
        self.flow_bbox = ( float("inf"), float("inf"), float("-inf"), float("-inf") )

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


    def _write_file (self, folder, filename, filedata, flags='w'):
        """Write the file data to the folder and filename combination
        (flags: 'w' for write text, 'wb' for write binary, use 'a' instead of 'w' for append)"""
        result = False
        if os.path.isdir(folder):
            try:
                file_obj = open(os.path.join(folder, filename), flags)
                file_obj.write(filedata)
                file_obj.close()
                result = True
            except IOError:
                pass
        return result

    def _determine_image_type (self, stream_first_4_bytes):
        """Find out the image file type based on the magic number comparison of the first 4 (or 2) bytes"""
        file_type = None
        bytes_as_hex = b2a_hex(stream_first_4_bytes)
        if bytes_as_hex.startswith('ffd8'):
            file_type = '.jpeg'
        elif bytes_as_hex == '89504e47':
            file_type = '.png'
        elif bytes_as_hex == '47494638':
            file_type = '.gif'
        elif bytes_as_hex.startswith('424d'):
            file_type = '.bmp'
        return file_type

    def save_images (self, images_folder):
        """Try to save the image data from this LTImage object, and return the file name, if successful"""
        result = None
        for page in self.pages:
            for segment in page.segments:
                for line in segment.lines:
                    if isinstance(line, LTImage) and line.stream:
                        file_stream = line.stream.get_rawdata()
                        if file_stream:
                            file_ext = self._determine_image_type(file_stream[0:4])
                            if file_ext:
                                file_name = ''.join([str(page.page_num), '_', line.name, file_ext])
                                if self._write_file(images_folder, file_name, file_stream, flags='wb'):
                                    result = file_name
        return result


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

                used_segments = list()
                text_list = list()
                for section in self.sections:
                    used_segments.extend(section.segments)
                    text_list.append(section.text())

                for page in self.pages:
                    for segment in page.segments:
                        if segment not in used_segments:
                            text_list.append(segment.text())

                text_list, tags, candidate_matrix = XML_Parser.generate_candidate_matrix(text_list)

                used_segments, used_indexes = [], []
                for col in range(candidate_matrix.shape[1]):
                    tag = tags[col][1]
                    feature = tags[col][0]
                    min_score = float("inf")
                    best_index = -1
                    for i in range(len(text_list)):
                        score = candidate_matrix[i][col]
                        if score < min_score:
                            min_score = score
                            best_index = i

                    if best_index < len(self.sections):
                        for segment in self.sections[best_index].segments:
                            segment.tag = tag
                            used_segments.append(segment)
                    else:
                        for page in self.pages:
                            for segment in page.segments:
                                if segment not in used_segments:
                                    if segment.text() == text_list[best_index]:
                                        segment.tag = tag


                for page in self.pages:
                    page.save_segments("./"+self.name+"_segments/")


    def _is_within_flow_bounds(self, segment):
        return segment.bbox[0] >= self.flow_bbox[0]-10.0 and segment.bbox[1] >= self.flow_bbox[1]-10.0 and segment.bbox[2] <= self.flow_bbox[2]+10.0 and segment.bbox[3] <= self.flow_bbox[3]+10.0

    def identify_sections(self):

        current_section = list()
        segments_used = list()
        for page in reversed(self.pages):
            sorted_segments = sorted(page.segments, key=lambda seg: -seg.bbox[2] )
            sorted_segments = sorted(sorted_segments, key=lambda seg: seg.bbox[1] )
            self.column_dim = sorted(self.column_dim, key=lambda x: x[0], reverse=True)
            for column in self.column_dim:
                for segment in sorted_segments:
                    if self._is_within_flow_bounds(segment) and segment.bbox[0] >= column[0]-10.0 and segment.bbox[2] <= column[1]+10.0:

                        if segment.font_size > self.default_size:
                            current_section = list(reversed(current_section))
                            section = Section(segment.text(), current_section)
                            if len(current_section) > 0:
                                self.sections.append(section)
                            current_section = list()
                        elif math.fabs(segment.font_size - self.default_size) < 1.0: #TODO improve condition, this is merging authors and affiliations together
                            segments_used.append(segment)
                            current_section.append(segment)

        self.sections = list(reversed(self.sections))


    def identify_num_columns(self):
        column_count = dict()
        self.column_dim = list()
        column_dim_list = list()
        for page in self.pages:
            column_dim = list()
            for segment in page.segments:
                if segment.font_family == self.default_font_family and math.fabs(segment.font_size - self.default_size) < 0.1:
                    column_dim_copy = list(column_dim)
                    updated_dim = False

                    for dim in column_dim_copy:
                        if math.fabs(segment.bbox[0] - dim[0]) < 10.0:
                            column_dim.remove(dim)
                            minx = segment.bbox[0] if segment.bbox[0] < dim[0] else dim[0]
                            maxx = segment.bbox[2] if segment.bbox[2] > dim[1] else dim[1]
                            column_dim.append( (minx, maxx) )
                            updated_dim = True
                            break

                    if updated_dim == False:
                        column_dim.append( (segment.bbox[0], segment.bbox[2]) )


                    minx_flow = self.flow_bbox[0] if self.flow_bbox[0] < segment.bbox[0] else segment.bbox[0]
                    miny_flow = self.flow_bbox[1] if self.flow_bbox[1] < segment.bbox[1] else segment.bbox[1]
                    maxx_flow = self.flow_bbox[2] if self.flow_bbox[2] > segment.bbox[2] else segment.bbox[2]
                    maxy_flow = self.flow_bbox[3] if self.flow_bbox[3] > segment.bbox[3] else segment.bbox[3]

                    self.flow_bbox = (minx_flow, miny_flow, maxx_flow, maxy_flow)

            column_dim_list.append( column_dim )

            if len(column_dim) in column_count:
                column_count[ len(column_dim) ] += 1
            else:
                column_count[ len(column_dim) ] = 1

        self.num_columns = find_most_frequent_item(column_count)

        for column_dim in column_dim_list:
            for dim in column_dim:
                updated = False
                for column_index in range(self.num_columns):

                    if dim[0] >= self.flow_bbox[0] + ((self.flow_bbox[2] - self.flow_bbox[0]) / self.num_columns) * column_index and \
                        dim[1] <= self.flow_bbox[0] + ((self.flow_bbox[2] - self.flow_bbox[0]) / self.num_columns) * (column_index+1):
                        for i in range(len(self.column_dim)):
                            test_dim = self.column_dim[i]
                            if math.fabs(test_dim[0] - dim[0]) < 10.0 and math.fabs(test_dim[1] - dim[1]) < 10.0:
                                minx = test_dim[0] if test_dim[0] < dim[0] else dim[0]
                                maxx = test_dim[1] if test_dim[1] > dim[1] else dim[1]
                                self.column_dim[i] = (minx, maxx)
                                updated = True
                                break

                        if updated == False:
                            self.column_dim.append( (dim[0], dim[1]) )


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




