from .document import Document


def ir_to_markdown(doc: Document) -> str:
    return doc.to_markdown()


def ir_to_xhtml(doc: Document) -> str:
    return doc.to_xhtml()


def xhtml_to_ir(xhtml: str) -> Document:
    return Document.from_xhtml(xhtml)


def markdown_to_ir(markdown: str) -> Document:
    return Document.from_markdown(markdown)
