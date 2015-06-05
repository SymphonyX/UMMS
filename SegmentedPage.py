from pdfminer.layout import *
import Image, ImageDraw, ImageFile
import math

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
        self.font = ""
        self.font_size = 0
        self.font_count = dict()
        self.bbox =(float("inf"), float("inf"), float("-inf"), float("-inf"))
        self.left_neighbor = None
        self.right_neighbor = None
        self.top_neighbor = None
        self.bottom_neighbor = None

    def determine_bounding_box(self):
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

    def top_center(self):
        return (self.bbox[0] + ((self.bbox[2] - self.bbox[0]) / 2.0), self.bbox[3])

    def bottom_center(self):
        return (self.bbox[0] + ((self.bbox[2] - self.bbox[0]) / 2.0), self.bbox[1])

    def left_center(self):
        return (self.bbox[0], self.bbox[1] + ((self.bbox[3] - self.bbox[1]) / 2.0))

    def right_center(self):
        return (self.bbox[2], self.bbox[1] + ((self.bbox[3] - self.bbox[1]) / 2.0))

    def addLine(self, lt_line):
        self.lines.append(lt_line)

    def determine_frequent_font(self):
        for i, line in enumerate(self.lines):
            if isinstance(line, LTTextLine):
                for character in line._objs:
                    if isinstance(character, LTChar):
                        if character.fontname in self.font_count:
                            self.font_count[character.fontname] += 1
                        else:
                            self.font_count[character.fontname] = 1
                        self.font_size = character.size

        self.font = find_most_frequent_item(self.font_count)

    def __str__(self):
        string = ""
        for l in self.lines:
            if isinstance(l, LTTextLine):
                string += l.get_text()
        return string

    def __repr__(self):
        return self.__str__()


class Page(LTPage):

    @staticmethod
    def distance(point1, point2):
        return math.sqrt((point1[0] - point2[0])**2 + (point1[1] - point2[1])**2)

    def __init__(self, lt_page, page_number, jpg=None):
        self.page_num = page_number
        self.page = lt_page
        self.segments = list()
        self._parse_text()
        self.jpg = jpg

    def _jpg_with_bbox(self):
        jpg_copy = self.jpg.copy()
        draw = ImageDraw.Draw(jpg_copy)
        draw.setfill(0)

        color = "red"
        for segment in self.segments:
            for line in segment.lines:
                if isinstance(line, LTTextLine):
                    color = "red"
                elif isinstance(line, LTRect):
                    color = "blue"
                elif isinstance(line, LTCurve):
                    color = "yellow"
                elif isinstance(line, LTImage):
                    color = "green"
                bbox = line.bbox
                draw.rectangle([bbox[0], self.jpg.size[1]-bbox[3], bbox[2], self.jpg.size[1]-bbox[1]], fill=None, outline=color)

            if segment.top_neighbor is not None:
                top_center = segment.top_center()
                bottom_center = segment.top_neighbor.bottom_center()
                draw.line( (top_center[0], self.jpg.size[1]-top_center[1], bottom_center[0], self.jpg.size[1]-bottom_center[1]), fill=color)

        del draw
        return jpg_copy

    def save_line(self, path):
        ImageFile.MAXBLOCK = 2**30
        img = self._jpg_with_bbox()
        img.save(path+"page_1"+str(self.page_num)+".jpg", "JPEG", quality=100, optimize=True, progressive=True)

    def show_lines(self):
        img = self._jpg_with_bbox()
        img.show()

    def _parse_text(self):
        for element in self.page._objs:
            if isinstance(element, LTTextBox):
                for line in element._objs:
                    segment = Segment()
                    segment.addLine(line)
                    segment.determine_bounding_box()
                    segment.determine_frequent_font()
                    self.segments.append(segment)
            elif isinstance(element, LTRect) or isinstance(element, LTCurve) or isinstance(element, LTImage):
                segment = Segment()
                segment.addLine(element)
                segment.determine_bounding_box()
                self.segments.append(segment)
            elif isinstance(element, LTFigure):
                for line in element._objs:
                    segment = Segment()
                    segment.addLine(line)
                    segment.determine_bounding_box()
                    self.segments.append(segment)

    def find_segment_neighbors(self):
        tops = sorted(self.segments, key=lambda seg: seg.bbox[3], reverse=True)
        bottoms = sorted(self.segments, key=lambda seg: seg.bbox[1], reverse=True)
        lefts = sorted(self.segments, key=lambda seg: seg.bbox[0])
        rights = sorted(self.segments, key=lambda seg: seg.bbox[2])
        slack = 10

        for i, segment in enumerate(tops):
            if i == 0: continue
            done = False
            for neighbor in bottoms:
                if segment is not neighbor:
                    neighbor_bottom = neighbor.bottom_center()
                    segment_top = segment.top_center()
                    if neighbor_bottom[1]+slack < segment_top[1]:
                        done = True
                        break
                    if segment.top_neighbor == None:
                        segment.top_neighbor = neighbor
                    else:
                        y_diff = (segment.top_neighbor.bottom_center()[1] - segment_top[1]) - (neighbor_bottom[1] - segment_top[1])
                        if y_diff > slack or ((y_diff > -slack or y_diff < slack) and Page.distance(segment.top_neighbor.bottom_center(), segment_top) > Page.distance(neighbor_bottom, segment_top)):
                            segment.top_neighbor = neighbor








