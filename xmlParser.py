import xml.etree.ElementTree as ET
from sklearn.feature_extraction.text import CountVectorizer
import numpy as np

OTHER_TAG = "other"
TITLE_TAG = "article-title"
CONTRIBUTOR_TAG ="contrib"
AUTHOR_TAG = "authors"
AFFILIATION_TAG = "aff"
ABSTRACT_TAG = "abstract"
SECTION_TAG = "sec"
FIGURE_TAG = "fig"

SECTION_BODY_TAG = "section-body"
CAPTION_TAG = "caption"
STAGE_FRONT = "front"
STAGE_BODY = "body"
STAGE_BACK = "back"

TAGS_OF_INTEREST = [TITLE_TAG, CONTRIBUTOR_TAG, AUTHOR_TAG, AFFILIATION_TAG, ABSTRACT_TAG, SECTION_TAG]

parsed_xml = dict()
bag_of_words = dict()

class Feature:

    def __init__(self, feature, text):
        self.feat = feature
        self.text = text

class XML_Parser:

    processing_tag_for_tag = { CONTRIBUTOR_TAG: "name",
                               AFFILIATION_TAG: "addr-line",
                               SECTION_TAG: "title" }
    STAGE = ""
    VECTORIZER = None

    @staticmethod
    def parse_file(file_path):
        tree = ET.parse(file_path)
        root = tree.getroot()
        XML_Parser._process_element(root)

        corpus = [k for k, v in parsed_xml.items()]
        XML_Parser.VECTORIZER = CountVectorizer(ngram_range=(2, 4), token_pattern=r'\s\w+\s', min_df=1)
        XML_Parser.VECTORIZER.fit_transform(corpus)
        analyzer = XML_Parser.VECTORIZER.build_analyzer()
        for k, v in parsed_xml.items():
            if len(analyzer(k)) > 0:
                feat = XML_Parser.VECTORIZER.transform([k]).toarray()
                feature = Feature(feat, k)
                bag_of_words[feature] = v

    @staticmethod
    def _recognized_element(element):
        if element.tag == ABSTRACT_TAG:
            return True
        elif element.tag == TITLE_TAG and XML_Parser.STAGE == STAGE_FRONT:
            return  True
        elif element.tag == CONTRIBUTOR_TAG:
            return True
        elif element.tag == AFFILIATION_TAG:
            return True
        elif element.tag == SECTION_TAG and XML_Parser.STAGE == STAGE_BODY:
            return True
        return False

    @staticmethod
    def _process_element(element):
        for child in element._children:
            if child.tag == STAGE_FRONT and XML_Parser.STAGE == "":
                XML_Parser.STAGE = STAGE_FRONT
            elif child.tag == STAGE_BODY and XML_Parser.STAGE == STAGE_FRONT:
                XML_Parser.STAGE = STAGE_BODY
            elif child == STAGE_BACK and XML_Parser.STAGE == STAGE_BODY:
                XML_Parser.STAGE = STAGE_BACK

            element_found = False
            if XML_Parser._recognized_element(child) == True:

                if child.tag == SECTION_TAG:
                    XML_Parser._process_section(child)
                else:
                    XML_Parser._parse_section_under_tag(child.tag, child)
                element_found = True

            else:
                text = ""
                for e in child._children:
                    if e.text is not None and e.tag not in TAGS_OF_INTEREST:
                        text += e.text + " "
                parsed_xml[text] = OTHER_TAG


            if element_found == False:
                XML_Parser._process_element(child)

    @staticmethod
    def _process_section(element):
        XML_Parser._parse_section_under_tag(element.tag, element)
        ######### For parsing section body only ###############
        body_text = ""
        for e in element._children:
            if e.tag == "p":
                body_text += e.text + " "
                parsed_xml[body_text] = SECTION_BODY_TAG
            elif e.tag == SECTION_TAG:
                XML_Parser._process_section(e)
            elif e.tag == FIGURE_TAG:
                caption_title, caption_body = XML_Parser._process_caption(e)
                if caption_body != "":
                    parsed_xml[caption_body] = "caption-body"
                if caption_title != "":
                    parsed_xml[caption_title] = "caption-title"

    @staticmethod
    def _process_caption(element):
        caption_title = ""
        caption_body = ""
        for child in element._children:
            if child.tag == "caption":
                for e in child._children:
                    if e.tag == "title" and (e.text is not None and e.text != "\n"):
                        caption_title += e.text + " "
                    elif e.tag == "p" and (e.text is not None and e.text != "\n"):
                        caption_body += e.text + " "
        return caption_title, caption_body


    @staticmethod
    def _parse_section_under_tag(tag, element):
        processing_element =  XML_Parser._get_processing_element(element)
        text = "" if processing_element.text == "\n" else processing_element.text
        for child in processing_element._children:
            text += child.text + " "

        parsed_xml[text] = tag


    @staticmethod
    def _get_processing_element(element):
        e = element
        if element.tag == CONTRIBUTOR_TAG or element.tag == AFFILIATION_TAG or element.tag == SECTION_TAG:
            for child in element._children:
                if child.tag == XML_Parser.processing_tag_for_tag[element.tag]:
                    e = child
        return e

    @staticmethod
    def _find_tag_for_text(text):
        feature_vec = XML_Parser.VECTORIZER.transform( [text] ).toarray()
        distance = np.infty
        text_tag = ""
        for feature, tag in bag_of_words.items():
            vec_distance = np.linalg.norm(feature.feat-feature_vec)
            if vec_distance < distance:
                distance = vec_distance
                text_tag = tag
        return text_tag

