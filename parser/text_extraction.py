import fitz  # PyMuPDF

def extract_text_from_two_columns(pdf_path):
    """
    Extracts text from a two-column structured PDF, attempting to preserve column order.
    """
    doc = fitz.open(pdf_path)
    extracted_text = []

    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        
        # Get text blocks with their bounding boxes
        blocks = page.get_text("blocks")
        
        # Sort blocks by their x-coordinate to separate columns
        # This assumes a clear vertical separation between columns
        blocks.sort(key=lambda block: block[0]) # Sort by x0 of bounding box

        # Heuristic to identify columns:
        # Assuming two distinct columns, we can find a vertical dividing line.
        # This might need adjustment based on the specific PDF's layout.
        
        column1_blocks = []
        column2_blocks = []
        
        # Find the approximate center x-coordinate to divide columns
        if blocks:
            # A simple approach for finding the dividing line. 
            # More robust methods might involve analyzing x-coordinates of all blocks.
            max_x = max(block[2] for block in blocks) # max x2
            min_x = min(block[0] for block in blocks) # min x0
            mid_x = (max_x + min_x) / 2

            for block in blocks:
                if block[0] < mid_x: # If block starts before the midpoint, it's likely in column 1
                    column1_blocks.append(block)
                else: # Otherwise, it's likely in column 2
                    column2_blocks.append(block)
        
        # Sort blocks within each column by their y-coordinate for reading order
        column1_blocks.sort(key=lambda block: block[1]) # Sort by y0
        column2_blocks.sort(key=lambda block: block[1]) # Sort by y0

        # Extract text from each column
        page_text = []
        for i in range(max(len(column1_blocks), len(column2_blocks))):
            if i < len(column1_blocks):
                page_text.append(column1_blocks[i][4]) # block[4] contains the text
            if i < len(column2_blocks):
                page_text.append(column2_blocks[i][4])

        extracted_text.append("\n".join(page_text))

    doc.close()
    return "\n\n".join(extracted_text)

if __name__ == "__main__":
    print(extract_text_from_two_columns("data/raw/SingaporeAsiaTaxonomy.pdf"))


