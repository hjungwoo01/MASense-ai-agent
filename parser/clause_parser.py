from dataclasses import dataclass, asdict
import re, json, hashlib
from pathlib import Path
import pdfplumber
import os
from typing import List, Dict, Tuple
import fitz

@dataclass
class Clause:
    id: str
    doc_id: str
    page: int
    section_path: list[str]     # ["Energy","Solar", "Eligibility criteria"]
    kind: str                   # "criterion" | "threshold" | "definition" | "dns_h" | "safeguard" | "note"
    text: str
    refs: dict                  # {"doc":"MAS SAT v1.0","page":12} => to use it when citing evidence


PUA = re.compile(r'[\uE000-\uF8FF]')  # Private Use Area => icon fonts, which can be a noise to our text dataset
END_PUNCT = re.compile(r'[.!?)]["”\']?\s*$')


# remove any whitespaces for a more efficient parsing and chunking
def clean_text(s: str) -> str:
    s = PUA.sub("", s)                        # drop private-use glyphs
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _largest_gap_split(xs: List[float], min_gap: float) -> float | None:
    """Return x split where the largest gap between sorted centers occurs, if big enough."""
    if len(xs) < 2: return None
    xs = sorted(xs)
    gaps = [(xs[i+1] - xs[i], (xs[i+1] + xs[i])/2) for i in range(len(xs)-1)]
    gap, split = max(gaps, key=lambda t: t[0])
    return split if gap >= min_gap else None

def pdf_to_text_by_page_two_columns(pdf_path: Path) -> List[Dict]:
    out = []
    with fitz.open(pdf_path) as doc:
        for pno, page in enumerate(doc, start=1):
            blocks = page.get_text("blocks")  # (x0,y0,x1,y1,text, block_no, block_type, ...)
            # keep text blocks with content
            blocks = [b for b in blocks if len(b) >= 5 and b[4] and clean_text(b[4])]
            if not blocks:
                out.append({"page": pno, "text": ""}); continue

            # Compute centers and page-dependent min gap (~10% of page width)
            W = page.rect.width
            centers = [((b[0]+b[2])/2.0) for b in blocks]
            split = _largest_gap_split(centers, min_gap=0.10 * W)

            if split is None:
                # Single-column (or no clear split): just sort top->bottom, left->right
                blocks.sort(key=lambda b: (b[1], b[0]))
                text = "\n".join(clean_text(b[4]) for b in blocks)
            else:
                left  = [b for b in blocks if (b[0]+b[2])/2.0 <= split]
                right = [b for b in blocks if (b[0]+b[2])/2.0  > split]
                left.sort(key=lambda b: (b[1], b[0]))
                right.sort(key=lambda b: (b[1], b[0]))
                # Read entire left column, then entire right column
                text_left  = "\n".join(clean_text(b[4]) for b in left)
                text_right = "\n".join(clean_text(b[4]) for b in right)
                text = "\n".join([t for t in (text_left, text_right) if t.strip()])

            out.append({"page": pno, "text": text})
    return out


def make_id(doc_id, page, text):
    h = hashlib.sha1(text.encode()).hexdigest()[:8]
    return f"{doc_id}-p{page}-{h}"

def pdf_to_text_by_page(pdf_path: Path) -> list[dict]:
    # minimal placeholder extractor; swap for pdfplumber/pymupdf as needed
    docs = []
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            txt = page.extract_text() or ""
            docs.append({"page": i, "text": txt})
    return docs

# stores each line as an element in a list
def detect_section_lines(text: str) -> list[str]:
    # loose heuristic: capture Heading-like lines
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    return lines

# need to add more keywords to classify key sections
def classify_kind(line: str) -> str:
    l = line.lower()
    if any(k in l for k in ["must", "shall", "required", "eligibility"]): return "criterion"
    if any(k in l for k in ["threshold", "intensity", "gco2", "capex","<",">","≤","≥"]): return "threshold"
    if any(k in l for k in ["do no significant harm","dnsh"]): return "dns_h"
    if any(k in l for k in ["minimum safeguards","governance","social"]): return "safeguard"
    if any(k in l for k in ["definition", "means", "refers to", "is known as", "is called", "defined as"]): return "definition"
    return "note"


def parse_pdf_to_clauses(pdf_path: str, doc_id: str, taxonomy_name="MAS SAT") -> list[Clause]:
    pages = pdf_to_text_by_page_two_columns(Path(pdf_path))   # <— use the improved extractor
    clauses: list[Clause] = []
    section_stack: list[str] = []

    for pg in pages:
        # (optional) update section_stack here using heading detection if you’ve added it
        lines = detect_section_lines(pg["text"])              # or split into sentences/paragraphs
        for raw in lines:
            line = clean_text(raw)
            kind = classify_kind(line)
            cid = make_id(doc_id, pg["page"], line[:160])
            clauses.append(Clause(
                id=cid,
                doc_id=doc_id,
                page=pg["page"],
                section_path=[s for s in section_stack[-3:] if s],
                kind=kind,
                text=line,
                refs={"doc": taxonomy_name, "page": pg["page"]},
            ))
    return clauses

def dump_clauses(clauses, out_path: str):
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump([asdict(c) for c in clauses], f, ensure_ascii=False, indent=2)


def test():
    print("running")
    
    # Testing clean_text function
    print("Test clean_text:", clean_text("hiii.     my name is \n      erica jeon"))

    # Testing make_id function
    print("Test make_id:", make_id("doc1", 1, "This is a sample text for hashing."))

    # Testing pdf_to_markdown function
    # pdf_path = "data/raw/Application_of_SAT.pdf"
    # md_pages = pdf_to_text_by_page(Path(pdf_path))
    # print(f"Extracted {len(md_pages)} pages from PDF.")
    # print("First page text snippet:", md_pages[3]["text"][:400] if md_pages else "No pages extracted.")
    # print("Markdown page structure:", md_pages[3] if md_pages else "No pages extracted.")

    # Testing detect_section_lines function
    sample_text = "Section 1: Introduction\nThis is the introduction.\n\nSection 2: Criteria\nMust meet the following criteria."
    print("This is the sample test:", sample_text)
    print("Test detect_section_lines:", detect_section_lines(sample_text))

    # Testing classify_kind function
    test_lines = [
        "Projects must reduce emissions by at least 30%.",
        "The threshold for energy efficiency is set at 20%.",
        "Do No Significant Harm (DNSH) criteria must be met.",
        "Minimum safeguards include social and governance aspects.",
        "Renewable energy refers to sources like solar and wind.",
        "This is a general note about the project.",
        "MAS is the Monetary Authority of Singapore."
    ]

    for line in test_lines:
        print(f"Line: '{line}' => Classified as: '{classify_kind(line)}'")

    print("Test pdf_to_text_by_page_two_columns:")
    print(pdf_to_text_by_page_two_columns("data/raw/SingaporeAsiaTaxonomy.pdf")[9])  # print first page's text snippet

def run(directory_path:str, out_directory_path: str):
    print(f"Scanning directory: {directory_path} for MAS PDFs...")
    for filename in os.listdir(directory_path):
        if filename.lower().endswith(".pdf"):
            pdf_path = os.path.join(directory_path, filename)
            doc_id = os.path.splitext(filename)[0]
            print(f"Processing {pdf_path} with doc_id {doc_id}...")
            clauses = parse_pdf_to_clauses(pdf_path, doc_id)
            print(f"Parsed {len(clauses)} clauses from {filename}.")
            out_path = os.path.join(out_directory_path, f"{doc_id}_clauses.json")
            dump_clauses(clauses, out_path)
            print(f"Dumped clauses to {out_path}")

if __name__ == "__main__":
    test()
    run("data/raw", "data/parsed")

