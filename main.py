import streamlit as st
import nltk
from nltk.tokenize import sent_tokenize
import io
import tempfile
import re
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, ListFlowable, ListItem, Table, TableStyle
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
import pdfplumber
from collections import OrderedDict
from PyPDF2 import PdfReader, PdfWriter

# Function to ensure NLTK data is downloaded
@st.cache_resource
def download_nltk_data():
    try:
        # Check if punkt is already downloaded
        try:
            nltk.data.find('tokenizers/punkt')
        except LookupError:
            nltk.download('punkt')
        
        # Check if stopwords is already downloaded
        try:
            nltk.data.find('corpora/stopwords')
        except LookupError:
            nltk.download('stopwords')
            
        # Check if wordnet is already downloaded
        try:
            nltk.data.find('corpora/wordnet')
        except LookupError:
            nltk.download('wordnet')
            
        return True
    except Exception as e:
        st.error(f"Error downloading NLTK data: {str(e)}")
        return False

# Rest of your imports and functions remain the same...

def main():
    # Download required NLTK data at startup
    if not download_nltk_data():
        st.error("Failed to download required NLTK data. Please try again.")
        return

    st.title("📄 Enhanced Document Summarizer")
    
    # Rest of your main() function remains the same...

if __name__ == "__main__":
    main()
