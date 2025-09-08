import os
from pathlib import Path
from typing import List, Dict
import re
from langchain.text_splitter import RecursiveCharacterTextSplitter
import json


def chunk_by_section(json_path: str) -> List[str]:
    chunks = []

    if not os.path.exists(json_path):
        print(f"File {json_path} does not exist.")
        return []
    
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size = 1000,
        chunk_overlap = 200,
        separators = ["\n\n", "\n", " ", ""],
        length_function = len
    )

    for page_data in data:
        doc_id = page_data.get("doc_id")
        page_number = page_data.get("page")
        page_content = page_data.get("text", "")

        section_chunks = re.split(r'^(#+ .*?)\n', page_content, flags=re.MULTILINE)

        leading_text = section_chunks[0].strip()
        if leading_text:
            if len(leading_text.split()) > 500:
                sub_chunks = text_splitter.split_text(leading_text)
                for sub_chunk in sub_chunks:
                    chunks.append({
                        "doc_id": doc_id,
                        "section_title": f"Page {page_number} - Intro",
                        "page_number": page_number,
                        "text": sub_chunk
                    })
            else:
                chunks.append({
                    "doc_id": doc_id,
                    "section_title": f"Page {page_number} - Intro",
                    "page_number": page_number,
                    "text": leading_text
                })

        for j in range(1, len(section_chunks), 2):
            section_title = section_chunks[j].strip()
            section_text = section_chunks[j+1].strip()

            if len(section_text.split()) > 500:
                sub_chunks = text_splitter.split_text(section_text)
                for sub_chunk in sub_chunks:
                    chunks.append({
                        "doc_id": doc_id,
                        "section_title": section_title,
                        "page_number": page_number,
                        "text": sub_chunk
                    })
            else:
                chunks.append({
                    "doc_id": doc_id,
                    "section_title": section_title,
                    "page_number": page_number,
                    "text": section_text
                })

    print(f"Generated {len(chunks)} section chunks from documents in. {json_path}.")
    return chunks




    
    # for file_name in os.listdir(json_path):
    #     if file_name.endswith(".md"):
    #         file_path = os.path.join(json_path, file_name)
            
    #         with open(file_path, "r", encoding="utf-8") as f:
    #             content = f.read()

    #         lines = content.strip().split('\n')
    #         doc_id = lines[0].lstrip('# ').strip()

    #         page_sections = re.split(r'^(#+ .*?)\n', content, flags=re.MULTILINE)

    #         if len(page_sections) < 2:
    #             continue

    #         current_page = None
    #         for i in range(1, len(page_sections), 2):
    #             section_title = page_sections[i].strip()
    #             section_text = page_sections[i+1].strip()

    #             try:
    #                 current_page = int(re.search(r'\d+', section_title).group())
    #             except (AttributeError, ValueError):
    #                 print(f"Could not extract page number from header: {section_title}")
    #                 continue

    #             sections = re.split(r'^(#+ .*?)\n', section_text, flags=re.MULTILINE)

    #             if len(sections) < 2:
    #                 # If a page has no sections, treat the whole page as one section and chunk it as a whole
    #                 chunks.append({
    #                     "doc_id": doc_id,
    #                     "section_title": f"Page {current_page}",
    #                     "page_number": current_page,
    #                     "text": section_text
    #                 })
    #                 continue

    #             for j in range(1, len(sections), 2):
    #                 section_title = sections[j].strip()
    #                 section_text = sections[j+1].strip()

    #                 # Apply recursive text splitting to the large section text
    #                 if len(section_text.split()) > 500:
    #                     sub_chunks = text_splitter.split_text(section_text)
    #                     for sub_chunk in sub_chunks:
    #                         chunks.append({
    #                             "doc_id": doc_id,
    #                             "section_title": section_title,
    #                             "page_number": current_page,
    #                             "text": sub_chunk
    #                         })
    #                 else:
    #                     chunks.append({
    #                         "doc_id": doc_id,
    #                         "section_title": section_title,
    #                         "text": section_text
    #                     })
        
    #     print(f"Generated {len(chunks)} section chunks from documents in. {dir_path}.")
    #     return chunks
    
if __name__ == "__main__":
    json_path = "data/parsed/parsed_docs.json"
    all_chunks = chunk_by_section(json_path)

    if all_chunks:
        print(f"Sample chunk:\n{all_chunks[0:10]}")
