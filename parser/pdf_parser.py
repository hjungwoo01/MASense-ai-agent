import os 
from typing import List, Dict
from collections import defaultdict
from pathlib import Path
import json


from llama_parse import LlamaParse
os.environ["LLAMA_CLOUD_API_KEY"] = "llx-qPEKUa1y8j3an10YV4S62jVcsm7TVKIuB7sDNyE3zfciZUp9"



parsing_instruction = """
The provided documents outline the MAS Singapore Taxonomy, which defines sustainability criteria, eligibility requirements, technical screening criteria, thresholds, safeguards, and definitions across multiple sectors. 
The sectors covered include: Energy, Industrial, Carbon Capture and Sequestration, Agriculture and Forestry/Land Use, Construction and Real Estate, Waste and Circular Economy, Information and Communications Technology (ICT), and Transportation.

The documents contain:
- Many tables with structured criteria (e.g., activity, eligibility, thresholds, traffic-light classification of green/amber/red).
- Narrative explanations that provide context and guidance for applying the taxonomy.
- Notes, definitions, and safeguards that may not appear in tabular form but are important to capture.

When parsing, please:
- Extract tables faithfully, preserving rows and columns.
- Maintain the hierarchy of sections (sector → activity → eligibility criteria/thresholds).
- Clearly differentiate between criteria, thresholds, definitions, safeguards, and notes.
- Capture all numerical values, percentages, dates, and thresholds accurately.
- Preserve explanatory text so that parsed outputs are both precise and contextually rich.

Try to be exact and structured in your parsing so the output can later be used for structured querying or retrieval-augmented generation (RAG).
"""

# create a parser instance with the specified instructions
parser = LlamaParse(
    result_type = "markdown",
    verbose = True,
    parsing_instructions = parsing_instruction,
    skip_diagonal_text = True
)


# define function to parse documents in a directory
def parse_documents(dir_path: str) -> List[Dict]:
    """
    Returns a list of dicts like:
    { 'doc_id': <pdf_name>, 'page': <int>, 'text': <str>, 'metadata': <dict> }
    """
     
    parsed_docs = []

    if not os.path.isdir(dir_path):
        print(f"Directory {dir_path} does not exist.")
        return []

    for file_name in os.listdir(dir_path):
        if file_name.endswith(".pdf"):
            file_path = os.path.join(dir_path, file_name)
            print(f"Processing {file_name}...")

            try:
                document = parser.load_data(file_path)
            except Exception as e:
                print(f"Error processing {file_name}: {e}")
                continue

            for i, doc in enumerate(document, start = 1):
                parsed_docs.append({
                    "doc_id": file_name,
                    "page": i,
                    "text": doc.text,
                    "metadata": doc.metadata if hasattr(doc, "metadata") else {}
                })

            print(f"Extracted {len(document)} pages from {file_name}.")
    return parsed_docs

def docs_to_json(parsed_docs: List[dict], out_path: str):
    """
    Dumps the list of parsed docs to a JSON file.
    """
    out_dir = os.path.dirname(out_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(parsed_docs, f, ensure_ascii=False, indent=2)


def docs_to_md(parsed_docs: List[dict], out_dir_path: str) -> list[str]:
    """
    Groups parsed pages by doc_id and writes one .md per original PDF.
    Each page is prefixed with a level-2 heading: '## Page <n>'.
    Returns the list of written markdown paths.
    """
    # Ensure the output directory exists
    os.makedirs(out_dir_path, exist_ok=True)

    by_doc: dict[str, List[dict]] = defaultdict(list)
    for row in parsed_docs:
        by_doc[row["doc_id"]].append(row)

    written_paths: List[str] = []
    for doc_id, pages in by_doc.items():
        pages.sort(key=lambda r: r.get("page", 0))
        
        # Use the original file name as the title
        lines = [f"# {Path(doc_id).stem}\n"] 
        for p in pages:
            lines.append(f"## Page {p.get('page', 0)}")
            lines.append((p.get("text") or "").rstrip())
            lines.append("")  # blank line between pages

        md_path = os.path.join(out_dir_path, f"{Path(doc_id).stem}.md")
        with open(md_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        written_paths.append(md_path)
    
    return written_paths                         


def run(directory_path:str, out_directory_path: str):
    print(f"Scanning directory: {directory_path} for MAS PDFs...")
    parsed_docs = parse_documents(directory_path)
    if parsed_docs:
        print(f"Parsed {len(parsed_docs)} pages from PDFs in {directory_path}.")
        md_paths = docs_to_md(parsed_docs, out_directory_path)
        print(f"Wrote {len(md_paths)} markdown files to {out_directory_path}.")
    else:
        print("No documents were parsed.")


if __name__ == "__main__":
    run("data/raw", "data/parsed")







# document = LlamaParse(result_type="markdown").load_data("data/raw/SingaporeAsiaTaxonomy.pdf")

# documents_with_instructions = LlamaParse(
#     result_type="markdown",
#     parsing_instructions="These are the documents related to MAS taxonomy. Please ",
# ).load_data("data/raw/SingaporeAsiaTaxonomy.pdf")

# file_name = "Sample_mas_doc.md"
# with open(file_name, "w") as f:
#     f.write(documents_with_instructions[50].text)

# if __name__ == "__main__":
#     print(documents_with_instructions)