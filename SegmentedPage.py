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

    def bbox_centers(self):
        left_center = (self.bbox[0], (self.bbox[3] - self.bbox[1]) / 2.0)
        right_center = (self.bbox[2], (self.bbox[3] - self.bbox[1]) / 2.0)
        bottom_center = ( (self.bbox[2] - self.bbox[0]) / 2.0, self.bbox[1])
        top_center = ( (self.bbox[2] - self.bbox[0]) / 2.0, self.bbox[3])

        return (left_center, bottom_center, right_center, top_center)


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
            string += l.get_text()
        return string

    def __repr__(self):
        return self.__str__()


class Page(LTPage):

    def __init__(self, lt_page, page_number, jpg=None):
        self.page_num = page_number
        self.page = lt_page
        self.segments = list()
        self._parse_text()
        self.jpg = jpg

    def _jpg_with_bbox(self, mark_types="segments"):
        jpg_copy = self.jpg.copy()
        draw = ImageDraw.Draw(jpg_copy)
        draw.setfill(0)

        if mark_types == "segments":
            for segment in self.segments:
                bbox = segment.bbox
                draw.rectangle([bbox[0], self.jpg.size[1]-bbox[3], bbox[2], self.jpg.size[1]-bbox[1]], fill=None, outline="red")
        else: # mark_types == "lines":
            for segment in self.segments:
                for line in segment.lines:
                    bbox = line.bbox
                    draw.rectangle([bbox[0], self.jpg.size[1]-bbox[3], bbox[2], self.jpg.size[1]-bbox[1]], fill=None, outline="red")

        del draw
        return jpg_copy

    def save_segments(self, path):
        ImageFile.MAXBLOCK = 2**30
        img = self._jpg_with_bbox(mark_types="segments")
        img.save(path+"page_1"+str(self.page_num)+".jpg", "JPEG", quality=100, optimize=True, progressive=True)

    def save_line(self, path):
        ImageFile.MAXBLOCK = 2**30
        img = self._jpg_with_bbox(mark_types="lines")
        img.save(path+"page_1"+str(self.page_num)+".jpg", "JPEG", quality=100, optimize=True, progressive=True)


    def show_segments(self):
        img = self._jpg_with_bbox(mark_types="segments")
        img.show()

    def show_lines(self):
        img = self._jpg_with_bbox(mark_types="lines")
        img.show()

    def _parse_text(self):
        for element in self.page._objs:
            text, distances = [], []
            if isinstance(element, LTTextBox):
                for i, line in enumerate(element._objs):
                    if i == 0:
                        distances.append( (0, 0) )
                    else:
                        distances.append( (line.bbox[0] - element._objs[i-1].bbox[0], element._objs[i-1].bbox[1] - line.bbox[3]) )

                self._determine_segments(distances, element)

    def _line_belongs_to_segment(self, distances, line_index):
        if (distances[line_index][1] < 0) or \
                (line_index == len(distances)-1 and distances[line_index-1][1] - distances[line_index][1] < 5.0) or \
                (line_index < len(distances)-1 and distances[line_index][1] - distances[line_index+1][1] < 1.0):
            return True

        return False

    def _determine_segments(self, distances, element):
        newSegment = Segment()
        self.segments.append(newSegment)
        for i, dis in enumerate(distances):
            line = element._objs[i]
            if i == 0:
                newSegment.addLine(line)
            else:
                #Only looking at vertical distance now...Not quite right yet.
                if self._line_belongs_to_segment(distances, i):
                    newSegment.addLine(line)
                else:
                    newSegment.determine_frequent_font()
                    newSegment.determine_bounding_box()
                    newSegment = Segment()
                    self.segments.append(newSegment)
                    newSegment.addLine(line)
        newSegment.determine_frequent_font()
        newSegment.determine_bounding_box()





