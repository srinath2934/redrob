
import os
import zipfile
import xml.etree.ElementTree as ET

def extract_docx_text(docx_path):
    try:
        with zipfile.ZipFile(docx_path) as z:
            xml_content = z.read('word/document.xml')
            root = ET.fromstring(xml_content)
            paragraphs = []
            # Namespace map for WordprocessingML
            ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
            
            # Find all paragraph elements
            for para in root.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p'):
                text_runs = []
                for run in para.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}r'):
                    # Check for text or tab elements
                    t_nodes = run.findall('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t')
                    text_runs.append(''.join(t.text for t in t_nodes if t.text))
                paragraphs.append(''.join(text_runs))
            return '\n'.join(paragraphs)
    except Exception as e:
        return f"Error reading {docx_path}: {e}"

def main():
    dir_path = r"d:\redrob\[PUB] India_runs_data_and_ai_challenge\India_runs_data_and_ai_challenge"
    files_to_convert = ["README.docx", "job_description.docx", "redrob_signals_doc.docx", "submission_spec.docx"]
    
    for filename in files_to_convert:
        path = os.path.join(dir_path, filename)
        if os.path.exists(path):
            text = extract_docx_text(path)
            out_filename = filename.replace(".docx", ".txt")
            out_path = os.path.join(dir_path, out_filename)
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(text)
            print(f"Successfully converted {filename} to {out_filename}")
        else:
            print(f"File not found: {path}")

if __name__ == "__main__":
    main()
