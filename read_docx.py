import zipfile
import xml.etree.ElementTree as ET
import os

def read_docx(file_path):
    if not os.path.exists(file_path):
        return f"File not found: {file_path}"
    
    try:
        with zipfile.ZipFile(file_path) as docx:
            xml_content = docx.read('word/document.xml')
            root = ET.fromstring(xml_content)
            
            # Namespaces
            ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
            
            paragraphs = []
            for paragraph in root.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p'):
                texts = [node.text for node in paragraph.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t') if node.text]
                if texts:
                    paragraphs.append("".join(texts))
            
            return "\n".join(paragraphs)
    except Exception as e:
        return f"Error reading docx: {str(e)}"

if __name__ == '__main__':
    doc_path = r"d:\FraudGraphShield\FraudGraph_Shield_Solution_Approach.docx"
    text = read_docx(doc_path)
    output_path = r"d:\FraudGraphShield\FraudGraph_Shield_Solution_Approach.txt"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"Successfully wrote {len(text)} characters to {output_path}")
