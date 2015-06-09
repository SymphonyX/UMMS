from pdfminer.layout import *

def find_most_frequent_item(dictionary):
    count = 0
    frequent_item = ""
    for k, v in dictionary.items():
        if v > count:
            count = v
            frequent_item = k

    return frequent_item


class Segment:

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

    def _determine_bounding_box(self):
        x0 = float("inf")
        x1 = float("-inf")
        y0 = float("inf")
        y1 = float("-inf")
        for line in self.lines:
            if line.bbox[0] < x0:
                x0 = line.bbox[0]
            if line.bbox[1] < y0:
                y0 = line.bbox[1]
            if line.bbox[2] > x1:
                x1 = line.bbox[2]
            if line.bbox[3] > y1:
                y1 = line.bbox[3]

        self.bbox = (x0, y0, x1, y1)

    def contains_figure(self):
        for line in self.lines:
            if isinstance(line, LTTextLine) == False:
                return True
        return False

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

    def _determine_frequent_font(self):
        for i, line in enumerate(self.lines):
            if isinstance(line, LTTextLine):
                for character in line._objs:
                    if isinstance(character, LTChar):
                        if character.fontname in self.font_count:
                            self.font_count[character.fontname] += 1
                        else:
                            self.font_count[character.fontname] = 1
                        self.font_size = character.size

        font = find_most_frequent_item(self.font_count).split(",")
        self.font_family = font[0]
        self.font_type =  "Regular" if len(font) == 1 else font[1]

    def __str__(self):
        string = ""
        for l in self.lines:
            if isinstance(l, LTTextLine):
                u = l.get_text().decode('cp1251')  # decode from cp1251 byte (str) string to unicode string
                s = u.encode('utf-8')
                string += l.get_text()
        return string

    def __repr__(self):
        return self.__str__()