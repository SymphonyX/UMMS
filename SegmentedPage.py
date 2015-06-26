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
            if style == "lines":
                for line in segment.lines:
                    if isinstance(line, LTTextLine):
                        color = "red"
                    elif isinstance(line, LTRect):
                        color = "blue"
                    elif isinstance(line, LTCurve):
                        color = "yellow"
                    elif isinstance(line, LTImage):
                        color = "green"
                    color = "red" if line.bbox[1] == line.bbox[3] else color

                    bbox = line.bbox if line.bbox[1] != line.bbox[3] else (line.bbox[0], line.bbox[1], line.bbox[2], line.bbox[1]+2)
                    draw.rectangle([bbox[0], self.jpg.size[1]-bbox[3], bbox[2], self.jpg.size[1]-bbox[1]], fill=None, outline=color)
            elif style == "segments":
                bbox = segment.bbox
                draw.rectangle([bbox[0], self.jpg.size[1]-bbox[3], bbox[2], self.jpg.size[1]-bbox[1]], fill=None, outline="black")
                draw.text([bbox[0], self.jpg.size[1]-bbox[1]], segment.tag, fill="red")
                for line in segment.lines:
                    if line.bbox[1] == line.bbox[3]:
                        bbox = (line.bbox[0], line.bbox[1], line.bbox[2], line.bbox[1]+10)
                        draw.rectangle([bbox[0], self.jpg.size[1]-bbox[3], bbox[2], self.jpg.size[1]-bbox[1]], fill=None, outline="red")


            if segment.top_neighbor is not None:
                top_center = segment.top_center()
                bottom_center = segment.top_neighbor.bottom_center()
                draw.line( (top_center[0], self.jpg.size[1]-top_center[1], bottom_center[0], self.jpg.size[1]-bottom_center[1]), fill=color)

        del draw
        return jpg_copy

    def save_line(self, path):
        ImageFile.MAXBLOCK = 2**50
        img = self._jpg_with_bbox()
        img.save(path+"page_"+str(self.page_num)+".jpg", "JPEG", quality=60, optimize=True, progressive=True)

    def show_lines(self):
        img = self._jpg_with_bbox(style="lines")
        img.show()

    def save_segments(self, path):
        ImageFile.MAXBLOCK = 2**50
        img = self._jpg_with_bbox(style="segments")
        img.save(path+"page_"+str(self.page_num)+".jpg", "JPEG", quality=60, optimize=True, progressive=True)

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

    def _is_reference_marker(self, segment):
        return len(segment.lines) == 1 and isinstance(segment.lines[0], LTLine)

    def _similar_fonts(self, segment1, segment2):
        return math.fabs(segment1.font_size - segment2.font_size) < 1.0 and Segment.contains_similar_fonts(segment1, segment2)

    def _merge_segment_to_top(self, segment, top_neighbor):
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

    def concatenate_segments(self, distances):

        #Concatenate segments with top neighbors
        concatenating = True
        slack = 2
        while concatenating:
            concatenating = False
            self.segments = sorted(self.segments, key=lambda seg: seg.bbox[3])
            for i in range(len(self.segments)):
                segment = self.segments[i]
                top_neighbor = segment.top_neighbor
                segment_font_key = segment.key_for_font()

                if top_neighbor is not None and segment_font_key in distances:
                    median = np.median( distances[segment_font_key] )
                    std = np.std( distances[segment_font_key] )
                    distance_to_top = math.fabs(segment.top_center()[1] - top_neighbor.bottom_center()[1])
                    mean_line_distance, std_line_distance = segment.distance_between_lines()

                    min_distance = median
                    test_segment = segment
                    test_top = top_neighbor
                    test_distance_to_top = distance_to_top
                    while test_top is not None and self._similar_fonts(test_segment, test_top):
                        mean_line_distance_top, std_line_distance_top = test_top.distance_between_lines()
                        test_distance_to_top = math.fabs(test_segment.top_center()[1] - test_top.bottom_center()[1])

                        if mean_line_distance is not None and mean_line_distance < test_distance_to_top:
                            min_distance = mean_line_distance
                        elif test_distance_to_top < min_distance and mean_line_distance_top is None:
                            min_distance = test_distance_to_top
                        elif mean_line_distance_top is not None and  mean_line_distance_top < min_distance:
                            min_distance = mean_line_distance_top
                        test_segment = test_top
                        test_top = test_segment.top_neighbor


                    if self._is_reference_marker(top_neighbor) and distance_to_top < min_distance + slack:
                        self._merge_segment_to_top(segment, top_neighbor)
                        concatenating = True
                        break
                    elif self._similar_fonts(top_neighbor, segment) and distance_to_top < min_distance + slack:
                        self._merge_segment_to_top(segment, top_neighbor)
                        concatenating = True
                        break

        #Concatenate overlapping segments
        concatenating = True
        while concatenating:
            concatenating = False
            for i in range(len(self.segments)):
                segment = self.segments[i]
                for test_segment in self.segments:
                    if test_segment is not segment and Page.intersecting_segments(segment, test_segment):# and (self._is_reference_marker(test_segment) or self._similar_fonts(segment, test_segment)):
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








