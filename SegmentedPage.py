from pdfminer.layout import *
import Image, ImageDraw, ImageFile
import math
import numpy as np
from Segment import Segment


class Page(LTPage):

    @staticmethod
    def distance(point1, point2):
        return math.sqrt((point1[0] - point2[0])**2 + (point1[1] - point2[1])**2)

    @staticmethod
    def intersecting_columns(segment1, segment2):
        if segment1.bbox[0] < segment2.bbox[2] and segment1.bbox[2] > segment2.bbox[0]:
            return True
        elif segment2.bbox[0] < segment1.bbox[2] and segment2.bbox[2] > segment1.bbox[0]:
            return True
        return False

    @staticmethod
    def intersecting_row(segment1, segment2):
        if segment1.bbox[1] < segment2.bbox[3] and segment1.bbox[3] > segment2.bbox[1]:
            return True
        elif segment2.bbox[1] < segment1.bbox[3] and segment2.bbox[3] > segment1.bbox[1]:
            return True
        return False

    @staticmethod
    def intersecting_segments(segment1, segment2):
        return Page.intersecting_columns(segment1, segment2) and Page.intersecting_row(segment1, segment2)

    def __init__(self, lt_page, page_number, jpg=None):
        self.page_num = page_number
        self.page = lt_page
        self.segments = list()
        self._parse_text()
        self.jpg = jpg

    def _jpg_with_bbox(self, style="lines"):
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
            if style == "segments":
                bbox = segment.bbox
                draw.rectangle([bbox[0], self.jpg.size[1]-bbox[3], bbox[2], self.jpg.size[1]-bbox[1]], fill=None, outline="black")


            if segment.top_neighbor is not None:
                top_center = segment.top_center()
                bottom_center = segment.top_neighbor.bottom_center()
                draw.line( (top_center[0], self.jpg.size[1]-top_center[1], bottom_center[0], self.jpg.size[1]-bottom_center[1]), fill=color)

        del draw
        return jpg_copy

    def save_line(self, path):
        ImageFile.MAXBLOCK = 2**50
        img = self._jpg_with_bbox()
        img.save(path+"page_"+str(self.page_num)+".jpg", "JPEG", quality=100, optimize=True, progressive=True)

    def show_lines(self):
        img = self._jpg_with_bbox(style="lines")
        img.show()

    def save_segments(self, path):
        ImageFile.MAXBLOCK = 2**50
        img = self._jpg_with_bbox(style="segments")
        img.save(path+"page_"+str(self.page_num)+".jpg", "JPEG", quality=100, optimize=True, progressive=True)

    def show_segments(self):
        img = self._jpg_with_bbox()
        img.show()

    def _parse_text(self):
        for element in self.page._objs:
            if isinstance(element, LTTextBox):
                for line in element._objs:
                    segment = Segment()
                    segment.addLine(line)
                    self.segments.append(segment)
            elif isinstance(element, LTRect) or isinstance(element, LTCurve) or isinstance(element, LTImage):
                segment = Segment()
                segment.addLine(element)
                self.segments.append(segment)
            elif isinstance(element, LTFigure):
                for line in element._objs:
                    segment = Segment()
                    segment.addLine(line)
                    self.segments.append(segment)

    def _find_top_neighbor_for_segment(self, segment):
        bottoms = sorted(self.segments, key=lambda seg: seg.bbox[1], reverse=True)
        slack = 5

        for neighbor in bottoms:
            if segment is not neighbor:
                neighbor_bottom = neighbor.bottom_center()
                segment_top = segment.top_center()
                if neighbor_bottom[1]+slack < segment_top[1]:
                    break
                if segment.top_neighbor == None:
                    segment.top_neighbor = neighbor
                    neighbor.neighbor_to.append(segment)
                else:
                    #Prefer vertical distances
                    y_diff = (segment.top_neighbor.bottom_center()[1] - segment_top[1]) - (neighbor_bottom[1] - segment_top[1])
                    if Page.intersecting_columns(segment, neighbor) and (y_diff > 10  or ((y_diff > -1 or y_diff < 10) and Page.distance(segment.top_neighbor.bottom_center(), segment_top) > Page.distance(neighbor_bottom, segment_top))):
                        segment.top_neighbor.neighbor_to.remove(segment)
                        segment.top_neighbor = neighbor
                        neighbor.neighbor_to.append(segment)

    def find_segment_top_neighbors(self):
        tops = sorted(self.segments, key=lambda seg: seg.bbox[3], reverse=True)

        for i, segment in enumerate(tops):
            if i == 0: continue
            self._find_top_neighbor_for_segment(segment)

    def concatenate_top_neighbor(self):
        distances = list()
        for segment in self.segments:
            if segment.top_neighbor is not None:
                distance = Page.distance( (0, segment.top_center()[1]), (0, segment.top_neighbor.bottom_center()[1])  )
                distances.append( distance )

        mean = np.mean(distances)
        std = np.std(distances)

        #Concatenate segments with top neighbors
        concatenating = True
        while concatenating:
            concatenating = False
            for i in range(len(self.segments)):
                segment = self.segments[i]
                top_neighbor = segment.top_neighbor
                slack = 0 if (top_neighbor == None or top_neighbor.font_type != segment.font_type) else 10
                if top_neighbor is not None and (top_neighbor.font_size == segment.font_size and top_neighbor.font_family == segment.font_family) and Page.distance( (0, segment.top_center()[1]), (0, top_neighbor.bottom_center()[1]) ) < mean + slack:
                    for line in segment.lines:
                        top_neighbor.addLine(line)

                    self.segments.remove(segment)
                    top_neighbor.neighbor_to.remove(segment)

                    segment_neighbor = list(segment.neighbor_to)

                    for neighbor in top_neighbor.neighbor_to:
                        self._find_top_neighbor_for_segment(neighbor)
                    for neighbor in segment_neighbor:
                        neighbor.top_neighbor.neighbor_to.remove(neighbor)
                        neighbor.top_neighbor = None
                        self._find_top_neighbor_for_segment(neighbor)

                    concatenating = True
                    break

        #Concatenate overlapping segments
        concatenating = True
        while concatenating:
            concatenating = False
            for i in range(len(self.segments)):
                segment = self.segments[i]
                for test_segment in self.segments:
                    if test_segment is not segment and Page.intersecting_segments(segment, test_segment):
                        for line in test_segment.lines:
                            segment.addLine(line)

                        self.segments.remove(test_segment)

                        segment_neighbors = list(segment.neighbor_to)

                        for neighbor in test_segment.neighbor_to:
                            neighbor.top_neighbor = None
                            self._find_top_neighbor_for_segment(neighbor)
                        for neighbor in segment_neighbors:
                            neighbor.top_neighbor.neighbor_to.remove(neighbor)
                            neighbor.top_neighbor = None
                            self._find_top_neighbor_for_segment(neighbor)

                        concatenating = True
                if concatenating == True:
                    break








