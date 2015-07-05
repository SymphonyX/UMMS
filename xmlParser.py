import xml.etree.ElementTree as ET
from sklearn.feature_extraction.text import CountVectorizer
import numpy as np

OTHER_TAG = "other"
TITLE_TAG = "article-title"
CONTRIBUTOR_TAG ="contrib-group"
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


parsed_xml = dict()
bag_of_words = dict()

class Feature:

    def __init__(self, feature, text):
        self.feat = feature
        self.text = text

class XML_Parser:

    VECTORIZER = None

    @staticmethod
    def parse_file(file_path):
        tree = ET.parse(file_path)
        root = tree.getroot()
        XML_Parser._process_element(root)

        corpus = [k for k, v in parsed_xml.items()]
        #XML_Parser.VECTORIZER = CountVectorizer(ngram_range=(1, 3), token_pattern=r'\b\w+\b', min_df=1)
        XML_Parser.VECTORIZER = CountVectorizer(min_df=1)
        XML_Parser.VECTORIZER.fit_transform(corpus)
        analyzer = XML_Parser.VECTORIZER.build_analyzer()
        for k, v in parsed_xml.items():
            if len(analyzer(k)) > 0:
                feat = XML_Parser.VECTORIZER.transform([k]).toarray()
                feature = Feature(feat, k)
                bag_of_words[feature] = v

    @staticmethod
    def _process_element(element):
        for child in element._children:

            if child.tag == STAGE_FRONT:
                XML_Parser._process_front_elements(child)
            elif child.tag == STAGE_BODY:
                XML_Parser._process_body_elements(child)
            elif child.tag == STAGE_BACK:
                XML_Parser._process_back_elements(child)

    @staticmethod
    def _process_back_elements(element):
        for child in element._children:
            if child.tag == "ack":
                acknowledgement = ""
                for c in child._children:
                    if c.tag == "p":
                        acknowledgement += c.text + " "
                parsed_xml[acknowledgement] = "acknowledgement"
            elif child.tag == "ref-list":
                for c in child._children:
                    if c.tag == "title":
                        parsed_xml[c.text] = "reference-title"

    @staticmethod
    def _process_front_elements(element):
        for child in element._children:
            XML_Parser._process_front_elements(child)

        if element.tag == TITLE_TAG:
            parsed_xml[element.text] = TITLE_TAG
        elif element.tag == ABSTRACT_TAG:
            abstract = ""
            for child in element._children:
                if child.tag == "p":
                    abstract += child.text + " "
            parsed_xml[abstract] = ABSTRACT_TAG
        elif element.tag == CONTRIBUTOR_TAG:
            authors = ""
            for child in element._children:
                if child.tag == "contrib" and child.attrib["contrib-type"] == "author":
                    name_element = child._children[0]
                    for c in name_element._children:
                        authors += c.text + " "
                    authors += ", "

            if authors != "":
                parsed_xml[authors] = "authors"
        elif element.tag == "article-meta":
            affiliations = ""
            for child in element._children:
                if child.tag == "aff" and child.attrib["id"].startswith("edit") == False:
                    for c in child._children:
                        if c.tag == "addr-line":
                            affiliations += c.text + " "

            if affiliations != "":
                parsed_xml[affiliations] = AFFILIATION_TAG


    @staticmethod
    def _process_body_elements(element):
        for child in element._children:
            if child.tag == SECTION_TAG:
                XML_Parser._process_section(child)


    @staticmethod
    def _process_section(element):
        content = ""
        for child in element._children:
            if child.tag == "title":
                parsed_xml[child.text] = "section-title"
            elif child.tag == "p":
                if child.text is not None:
                    content += child.text + " "
                for c in child._children:
                    if c.tag == "xref":
                        content += c.tail + " "
                    elif c.tag == "italic":
                        content += c.text + " "
            elif child.tag == SECTION_TAG:
                XML_Parser._process_section(child)

        if content != "":
            parsed_xml[content] = "section-body"


    @staticmethod
    def generate_candidate_matrix(text_list):
        matrix = np.zeros( (len(text_list), len(bag_of_words.items())) ) #(text, tags)

        tags = list()
        for feature, tag in bag_of_words.items():
            tags.append( (feature, tag) )

        for i, text in enumerate(text_list):
            feature_vec = XML_Parser.VECTORIZER.transform( [text] ).toarray()
            index = 0
            for tup in tags:
                feature = tup[0]
                tag = tup[1]
                distance = np.linalg.norm(feature.feat-feature_vec)
                matrix[i][index] = distance
                index += 1

        return text_list, tags, matrix