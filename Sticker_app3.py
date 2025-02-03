import streamlit as st
import fitz  # PyMuPDF
from PIL import Image, ImageDraw, ImageFont
import os
import tempfile
import pandas as pd

# Constants for positioning
TOP_MARGIN = 50  # Distance from top of page for exhibit sticker
BOTTOM_MARGIN = 40  # Distance from bottom of page for page number
STICKER_ASPECT_RATIO = 70 / 250  # Maintain aspect ratio

# Function to generate an exhibit sticker
def create_exhibit_sticker(exhibit_number, sticker_width):
    sticker_height = sticker_width * STICKER_ASPECT_RATIO
    sticker_size = (int(sticker_width), int(sticker_height))

    background_color = "white"
    text_color = "red"

    # Create sticker image
    img = Image.new("RGB", sticker_size, background_color)
    draw = ImageDraw.Draw(img)

    # Use a fixed font size
    try:
        font = ImageFont.truetype("arial.ttf", int(sticker_width * 0.16))
    except IOError:
        font = ImageFont.load_default()

    # Define exhibit text
    text = f"Exhibit {exhibit_number}"

    # Calculate text size and center it
    text_bbox = draw.textbbox((0, 0), text, font=font)
    text_x = (sticker_size[0] - (text_bbox[2] - text_bbox[0])) // 2
    text_y = (sticker_size[1] - (text_bbox[3] - text_bbox[1])) // 2

    # Draw text
    draw.text((text_x, text_y), text, fill=text_color, font=font)

    # Save sticker
    sticker_path = f"exhibit_{exhibit_number}.png"
    img.save(sticker_path)
    return sticker_path, sticker_size  

# Function to generate a page number sticker (Now in Red)
def create_page_number_sticker(exhibit_number, page_number, sticker_width):
    sticker_height = sticker_width * (50 / 250)  # Maintain aspect ratio
    sticker_size = (int(sticker_width), int(sticker_height))

    background_color = "white"
    text_color = "red"

    # Create sticker image
    img = Image.new("RGB", sticker_size, background_color)
    draw = ImageDraw.Draw(img)

    # Use a smaller fixed font size
    try:
        font = ImageFont.truetype("arial.ttf", int(sticker_width * 0.12))
    except IOError:
        font = ImageFont.load_default()

    # Define page number text
    text = f"{exhibit_number}-{page_number}"

    # Calculate text size and center it
    text_bbox = draw.textbbox((0, 0), text, font=font)
    text_x = (sticker_size[0] - (text_bbox[2] - text_bbox[0])) // 2
    text_y = (sticker_size[1] - (text_bbox[3] - text_bbox[1])) // 2

    # Draw text
    draw.text((text_x, text_y), text, fill=text_color, font=font)

    # Save sticker
    sticker_path = f"page_{exhibit_number}_{page_number}.png"
    img.save(sticker_path)
    return sticker_path, sticker_size  

# Function to process PDFs
def process_pdf(uploaded_file, exhibit_number):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_pdf:
        temp_pdf.write(uploaded_file.read())
        temp_pdf_path = temp_pdf.name

    # Open the PDF
    doc = fitz.open(temp_pdf_path)

    # Get PDF page dimensions
    page_width, page_height = doc[0].rect.width, doc[0].rect.height

    # Calculate sticker sizes
    exhibit_sticker_width = page_width * 0.3  
    page_number_sticker_width = page_width * 0.2  

    # Generate exhibit sticker (only for first page)
    exhibit_sticker_path, exhibit_sticker_size = create_exhibit_sticker(exhibit_number, exhibit_sticker_width)

    # Insert exhibit sticker on the first page (Top Center)
    rect_exhibit = fitz.Rect(
        (page_width - exhibit_sticker_size[0]) / 2,
        TOP_MARGIN,
        (page_width + exhibit_sticker_size[0]) / 2,
        TOP_MARGIN + exhibit_sticker_size[1],
    )
    with open(exhibit_sticker_path, "rb") as sticker_file:
        doc[0].insert_image(rect_exhibit, stream=sticker_file.read())

    # Process each page to insert the page number
    for page_number, page in enumerate(doc, start=1):
        # Generate page number sticker
        page_sticker_path, page_sticker_size = create_page_number_sticker(exhibit_number, page_number, page_number_sticker_width)

        # Define position for page number (Bottom Center)
        rect_page_number = fitz.Rect(
            (page_width - page_sticker_size[0]) / 2,
            page_height - BOTTOM_MARGIN - page_sticker_size[1],
            (page_width + page_sticker_size[0]) / 2,
            page_height - BOTTOM_MARGIN,
        )

        # Insert page number sticker
        with open(page_sticker_path, "rb") as sticker_file:
            page.insert_image(rect_page_number, stream=sticker_file.read())

        # Remove temporary page number sticker
        os.remove(page_sticker_path)

    # Save processed PDF
    processed_pdf_path = f"processed_exhibit_{exhibit_number}.pdf"
    doc.save(processed_pdf_path)
    
    # **Close the PDF before deleting**
    doc.close()  

    # Cleanup temp file
    os.remove(temp_pdf_path)
    os.remove(exhibit_sticker_path)

    return processed_pdf_path

# Streamlit UI
st.title("📜 PDF Exhibit Sticker & Page Numbering Tool")
st.write("Upload multiple PDF files, reorder them, and process them with:")
st.markdown("- **Exhibit Sticker at the top center of the first page**")
st.markdown("- **Red Page Numbers at the bottom center of every page**")

# Upload multiple PDFs
uploaded_files = st.file_uploader("Upload PDFs", type=["pdf"], accept_multiple_files=True)

if uploaded_files:
    # Create a dataframe to store file order
    file_data = pd.DataFrame({"Filename": [file.name for file in uploaded_files], "Order": range(1, len(uploaded_files) + 1)})

    # Allow user to reorder files
    file_data = st.data_editor(file_data, use_container_width=True, num_rows="dynamic")

    # Sort files based on user-defined order
    sorted_files = [uploaded_files[i - 1] for i in file_data["Order"]]

    # Enter starting Exhibit Number
    exhibit_start = st.number_input("Enter Starting Exhibit Number:", min_value=1, step=1, value=1)

    if st.button("Process PDFs"):
        processed_files = []
        
        with st.spinner("Processing PDFs... Please wait."):
            for index, uploaded_file in enumerate(sorted_files):
                exhibit_number = exhibit_start + index
                processed_pdf_path = process_pdf(uploaded_file, exhibit_number)
                processed_files.append((exhibit_number, processed_pdf_path))

        st.success("✅ All PDFs processed successfully!")
        
        # Display download buttons for each processed PDF
        for exhibit_number, processed_pdf_path in processed_files:
            with open(processed_pdf_path, "rb") as file:
                st.download_button(
                    label=f"📥 Download Exhibit {exhibit_number}",
                    data=file,
                    file_name=f"Processed_Exhibit_{exhibit_number}.pdf",
                    mime="application/pdf"
                )

            # Remove processed file after downloading
            os.remove(processed_pdf_path)










