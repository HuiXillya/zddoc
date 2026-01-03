# import the zddoc module


import zddoc

if __name__ == "__main__":
    # Example usage of DocReader to read a .doc file
    from pathlib import Path
    from zddoc.reader import DocReader

    doc_path = Path(r"test_doc\a15a2-6pwn0.doc")  # Replace with your .doc file path
    try:
        with DocReader(doc_path) as reader:
            text = reader.read_text()
            print(text)
    except Exception as e:
        print("Error reading document:", e)