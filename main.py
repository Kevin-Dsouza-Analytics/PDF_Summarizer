import streamlit as st
import nltk
from nltk.tokenize import sent_tokenize
import io
import re
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, ListFlowable, ListItem, Table, TableStyle
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
import pdfplumber
from collections import OrderedDict
from PyPDF2 import PdfReader, PdfWriter

# Initialize session state for NLTK downloads
if 'nltk_downloaded' not in st.session_state:
    st.session_state.nltk_downloaded = False

# Download NLTK data with error handling
@st.cache_resource
def download_nltk_data():
    try:
        nltk.download('punkt', quiet=True)
        nltk.download('stopwords', quiet=True)
        nltk.download('wordnet', quiet=True)
        return True
    except Exception as e:
        st.error(f"Failed to download NLTK data: {str(e)}")
        return False

# Ensure NLTK data is downloaded
if not st.session_state.nltk_downloaded:
    st.session_state.nltk_downloaded = download_nltk_data()

def improve_section_extraction(text):
    """Enhanced section extraction with better header detection and string handling"""
    if not text:
        return OrderedDict()
        
    lines = text.split('\n')
    sections = OrderedDict()
    current_section = None
    current_subsection = None
    current_content = []

    header_patterns = [
        r'^#+\s+(.+)$',
        r'^([A-Z][A-Za-z\s]+:)$',
        r'^(\d+\.(?:\d+\.)*)\s+([A-Z][A-Za-z\s]+)',
        r'^([A-Z][A-Z\s]{3,})$'
    ]

    for line in lines:
        is_header = False
        for pattern in header_patterns:
            if re.match(pattern, line.strip()):
                is_header = True
                if current_section:
                    if current_subsection:
                        if not isinstance(sections.get(current_section), OrderedDict):
                            sections[current_section] = OrderedDict()
                        sections[current_section][current_subsection] = '\n'.join(current_content).strip()
                    else:
                        sections[current_section] = '\n'.join(current_content).strip()

                header_text = line.strip().lstrip('#').strip().capitalize()
                if re.match(r'^\d+\.\d+', header_text):
                    current_subsection = header_text
                else:
                    current_section = header_text
                    current_subsection = None
                current_content = []
                break

        if not is_header and (current_section or current_subsection):
            current_content.append(line)

    if current_section:
        if current_subsection:
            if not isinstance(sections.get(current_section), OrderedDict):
                sections[current_section] = OrderedDict()
            sections[current_section][current_subsection] = '\n'.join(current_content).strip()
        else:
            sections[current_section] = '\n'.join(current_content).strip()

    return sections

def extract_key_points(text, max_points=5):
    """Extract key points from text with enhanced error handling"""
    try:
        if not text or not isinstance(text, str):
            return []
            
        sentences = sent_tokenize(text)
        scores = {}
        
        important_keywords = {
            'mandatory': 2.5,
            'required': 2.2,
            'must': 2.2,
            'shall': 2.0,
            'critical': 1.8,
            'important': 1.8,
            'key': 1.5,
            'ensure': 1.4,
            'compliance': 1.4
        }

        for i, sentence in enumerate(sentences):
            score = 0
            if i == 0:
                score += 2.5
            elif i == len(sentences) - 1:
                score += 1.5
            else:
                score += 1.0 / (i + 1)

            lower_sentence = sentence.lower()
            for keyword, weight in important_keywords.items():
                if keyword in lower_sentence:
                    score += weight

            cleaned_sentence = re.sub(r'^[\-\*\•]\s*', '', sentence).strip()
            cleaned_sentence = re.sub(r'\*\*', '', cleaned_sentence)
            scores[cleaned_sentence] = score

        return [point[0] for point in sorted(scores.items(), key=lambda x: x[1], reverse=True)[:max_points]]
    except Exception as e:
        st.error(f"Error in key points extraction: {str(e)}")
        return []

def create_pdf_summary(sections, metrics):
    """Creates PDF summary with error handling"""
    try:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=72, leftMargin=72)
        styles = getSampleStyleSheet()
        content = []

        # Add title
        content.append(Paragraph("Document Summary", styles['Heading1']))
        content.append(Spacer(1, 20))

        # Add metrics table
        metrics_data = [
            ['Metric', 'Value'],
            ['Original Length', f"{metrics['original_words']} words"],
            ['Summary Length', f"{metrics['summary_words']} words"],
            ['Reduction', f"{metrics['reduction']}%"]
        ]
        
        table = Table(metrics_data)
        table.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ]))
        content.append(table)
        content.append(Spacer(1, 20))

        # Add sections
        for section_title, section_content in sections.items():
            content.append(Paragraph(section_title, styles['Heading2']))
            if isinstance(section_content, OrderedDict):
                for subsection_title, subsection_content in section_content.items():
                    content.append(Paragraph(subsection_title, styles['Heading3']))
                    points = extract_key_points(subsection_content)
                    for point in points:
                        content.append(Paragraph(f"• {point}", styles['Normal']))
            else:
                points = extract_key_points(section_content)
                for point in points:
                    content.append(Paragraph(f"• {point}", styles['Normal']))
            content.append(Spacer(1, 12))

        doc.build(content)
        buffer.seek(0)
        return buffer
    except Exception as e:
        st.error(f"Error creating PDF: {str(e)}")
        return None

def main():
    st.title("📄 Document Summarizer")
    st.markdown("Upload your PDF document to get a structured summary.")

    uploaded_file = st.file_uploader("Choose your PDF file", type="pdf")

    if uploaded_file is not None:
        try:
            with st.spinner("Processing document..."):
                # Extract text
                text = ""
                with pdfplumber.open(uploaded_file) as pdf:
                    for page in pdf.pages:
                        text += page.extract_text() or ""

                if not text.strip():
                    st.error("No text could be extracted from the PDF.")
                    return

                # Process sections
                sections = improve_section_extraction(text)
                
                # Calculate metrics
                original_words = len(text.split())
                summary_words = sum(
                    len(content.split()) if isinstance(content, str)
                    else sum(len(subcontent.split()) for subcontent in content.values())
                    for content in sections.values()
                )
                reduction_percentage = round((1 - summary_words/original_words) * 100, 1)

                metrics = {
                    'original_words': original_words,
                    'summary_words': summary_words,
                    'reduction': reduction_percentage
                }

                # Display results
                st.subheader("Summary Metrics")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Original Words", original_words)
                with col2:
                    st.metric("Summary Words", summary_words)
                with col3:
                    st.metric("Reduction", f"{reduction_percentage}%")

                # Create and offer PDF download
                pdf_buffer = create_pdf_summary(sections, metrics)
                if pdf_buffer:
                    st.download_button(
                        label="Download PDF Summary",
                        data=pdf_buffer,
                        file_name="document_summary.pdf",
                        mime="application/pdf"
                    )

                # Display sections
                st.subheader("Document Summary")
                for section_title, section_content in sections.items():
                    st.markdown(f"### {section_title}")
                    if isinstance(section_content, OrderedDict):
                        for subsection_title, subsection_content in section_content.items():
                            st.markdown(f"#### {subsection_title}")
                            for point in extract_key_points(subsection_content):
                                st.markdown(f"• {point}")
                    else:
                        for point in extract_key_points(section_content):
                            st.markdown(f"• {point}")

        except Exception as e:
            st.error(f"An error occurred while processing the document: {str(e)}")
            st.error("Please try again with a different PDF file.")

if __name__ == "__main__":
    main()
