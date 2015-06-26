from pdfminer.layout import *
import math
import numpy as np

def find_most_frequent_item(dictionary):
    count = 0
    frequent_item = ""
    for k, v in dictionary.items():
        if v > count:
            count = v
            frequent_item = k

    return frequent_item


class Segment:

    @staticmethod
    def contains_similar_fonts(segment1, segment2):
        for line in segment1.lines:
            if isinstance(line, LTTextLine):
                for element in line._objs:
                    if isinstance(element, LTChar):

                        for line2 in segment2.lines:
                            if isinstance(line2, LTTextLine):
                                for element2 in line2._objs:
                                    if isinstance(element2, LTChar):
                                        if element.fontname == element2.fontname:
                                            return True
        return False



    def __init__(self):
        self.lines = list()
        self.font_family = ""
        self.font_type = ""
        self.font_size = 0
        self.font_count = dict()
        self.bbox =(float("inf"), float("inf"), float("-inf"), float("-inf"))
        self.left_neighbor = None
        self.right_neighbor = None
        self.top_neighbor = None
        self.bottom_neighbor = None
        self.neighbor_to = list()
        self.tag = ""

    def _determine_bounding_box(self):
        x0 = float("inf")
        x1 = float("-inf")
        y0 = float("inf")
        y1 = float("-inf")
        for line in self.lines:
            if line.bbox[0] < x0:
                x0 = round(line.bbox[0],2)
            if line.bbox[1] < y0:
                y0 = round(line.bbox[1],2)
            if line.bbox[2] > x1:
                x1 = round(line.bbox[2],2)
            if line.bbox[3] > y1:
                y1 = round(line.bbox[3],2)

        self.bbox = (x0, y0, x1, y1)


    def contains_text(self):
        for line in self.lines:
            if isinstance(line, LTTextLine):
                return True
        return False

    def contains_figure(self):
        for line in self.lines:
            if isinstance(line, LTTextLine) == False:
                return True
        return False

    def key_for_font(self):
        return self.font_family + "-" + str(self.font_size)

    def top_center(self):
        return (self.bbox[0] + ((self.bbox[2] - self.bbox[0]) / 2.0), self.bbox[3])

    def bottom_center(self):
        return (self.bbox[0] + ((self.bbox[2] - self.bbox[0]) / 2.0), self.bbox[1])

    def left_center(self):
        return (self.bbox[0], self.bbox[1] + ((self.bbox[3] - self.bbox[1]) / 2.0))

    def right_center(self):
        return (self.bbox[2], self.bbox[1] + ((self.bbox[3] - self.bbox[1]) / 2.0))

    def addLine(self, lt_line):
        if lt_line not in self.lines:
            self.lines.append(lt_line)
            self._determine_bounding_box()
            self._determine_frequent_font()

    def distance_between_lines(self):
        distances = list()
        for i in range(len(self.lines)-1):
            distances.append( math.fabs(self.lines[i].y0 - self.lines[i+1].y1) )

        if len(distances) == 0:
            return None, None
        else:
            return np.mean(distances), np.std(distances)

    def _determine_frequent_font(self):
        size_count = dict()
        for i, line in enumerate(self.lines):
            if isinstance(line, LTTextLine):
                for character in line._objs:
                    if isinstance(character, LTChar):
                        if character.fontname in self.font_count:
                            self.font_count[character.fontname] += 1
                        else:
                            self.font_count[character.fontname] = 1
                        if character.size in size_count:
                            size_count[character.size] += 1
                        else:
                            size_count[character.size] = 1

        font = find_most_frequent_item(self.font_count)
        self.font = font
        split_font = self.font.split(",")
        self.font_family = split_font[0]
        self.font_type =  "Regular" if len(split_font) == 1 else split_font[1]
        size = find_most_frequent_item(size_count)
        self.font_size = 0 if size == "" else size

    def text(self):
        string = ""
        for l in self.lines:
            if isinstance(l, LTTextLine):
                #u = l.get_text().decode('cp1251')  # decode from cp1251 byte (str) string to unicode string
                #s = u.encode('utf-8')
                string += l.get_text()
        return string


    def __str__(self):
        return self.text()


    def __repr__(self):
        return self.__str__()