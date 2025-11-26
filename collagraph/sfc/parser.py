from __future__ import annotations

from html.parser import HTMLParser
from weakref import ref


class TextElement:
    def __init__(self, content, location=None):
        self.content = content
        self.location = location


class Comment:
    def __init__(self, content, location=None):
        self.content = content
        self.location = location


class Element:
    """Node that represents an element from a CGX file."""

    def __init__(self, tag: str, attrs: dict, location: tuple[int, int]):
        self.tag = tag
        self.attrs = attrs or {}
        self.location = location
        self.end: tuple[int, int] | None = None
        self.data: str | None = None
        self.children: list[Element | Comment | TextElement] = []
        self.parent: ref | None = None

    def child_with_tag(self, tag):
        for child in self.children:
            if getattr(child, "tag", None) == tag:
                return child


class CGXParser(HTMLParser):
    """Parser for CGX files.

    Creates a tree of Nodes with all encountered attributes and data.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.root = Element("root", attrs={}, location=(-1, -1))
        self.stack = [self.root]

    def _handle_tag(self, tag: str, attrs: list[tuple[str, str | None]]) -> Element:
        # The tag parameter is lower-cased by the HTMLParser.
        # In order to figure out whether the tag indicates
        # an imported class, we need the original casing for
        # the tag.
        # Using the original start tag, we can figure out where
        # the tag is located using a lower-cased version. And then
        # use the index to extract the original casing for the tag.
        complete_tag = self.get_starttag_text()
        index = complete_tag.lower().index(tag)
        original_tag = complete_tag[index : index + len(tag)]
        node = Element(original_tag, attrs=dict(attrs), location=self.getpos())

        # Cast attributes that have no value to boolean (True)
        # so that they function like flags
        for key, value in node.attrs.items():
            if value is None:
                node.attrs[key] = True

        # Add item as child to the last on the stack
        parent = self.stack[-1]
        parent.children.append(node)
        node.parent = ref(parent)

        return node

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]):
        node = self._handle_tag(tag, attrs)
        # Make the new node the last on the stack
        self.stack.append(node)

    def handle_endtag(self, tag: str):
        # pop it till popping the same tag in order to
        # work around unclosed tags?
        # Pop the stack until  (but not the root!)
        while len(self.stack) > 1:
            node = self.stack.pop()
            node.end = self.getpos()
            if node.tag.lower() == tag:
                break

    def handle_startendtag(self, tag: str, attrs):
        """Handle self-closing tags"""
        node = self._handle_tag(tag, attrs)
        # Get the full text and split it
        text = self.get_starttag_text()
        lines = text.splitlines()
        # Find the location of where the tag is actually closed
        column = lines[-1].index("/>")
        # Figure out how many lines the tag spans
        line_span_count = len(lines) - 1
        line, _ = self.getpos()
        # Set the end to be exactly where the '/>' is located
        node.end = (line + line_span_count, column)

    def handle_data(self, data: str):
        if data.strip():
            # Add item as child to the last on the stack
            self.stack[-1].children.append(
                TextElement(content=data, location=self.getpos())
            )

    def handle_comment(self, data: str):
        if data.strip():
            # Add item as child to the last on the stack
            self.stack[-1].children.append(
                Comment(content=data, location=self.getpos())
            )
