from packages.rag.src.rag.parsers.fda_parser import FDALabelParser
from packages.rag.src.rag.parsers.html_parser import HTMLParser
from packages.rag.src.rag.parsers.text_parser import TextParser


def test_text_parser_headings() -> None:
    content = """# Drug Overview
Lisinopril is an ACE inhibitor.

## Indications
Hypertension and heart failure.

## Contraindications
Do not use in pregnancy.
"""
    parser = TextParser()
    doc = parser.parse(content, title="Lisinopril")

    assert doc.title == "Lisinopril"
    assert len(doc.sections) == 3
    assert doc.sections[0].title == "Drug Overview"
    assert doc.sections[1].title == "Indications"
    assert "Hypertension" in doc.sections[1].content
    assert doc.sections[2].title == "Contraindications"
    assert doc.sections[2].section_path == "Lisinopril > Drug Overview > Contraindications"


def test_html_parser_strips_scripts_and_extracts_headings() -> None:
    html = """
    <html>
      <head><title>Metoprolol Prescribing Info</title></head>
      <body>
        <script>alert("ignore");</script>
        <h1>Clinical Pharmacology</h1>
        <p>Metoprolol is a beta1-selective adrenoceptor blocking agent.</p>
        <h2>Dosage</h2>
        <p>Initial dose is 100 mg daily in single or divided doses.</p>
      </body>
    </html>
    """
    parser = HTMLParser()
    doc = parser.parse(html)

    assert doc.title == "Metoprolol Prescribing Info"
    assert len(doc.sections) == 2
    assert doc.sections[0].title == "Clinical Pharmacology"
    assert "beta1-selective" in doc.sections[0].content
    assert "alert" not in doc.sections[0].content
    assert doc.sections[1].title == "Dosage"


def test_fda_label_parser() -> None:
    fda_record = {
        "id": "test_fda_1",
        "openfda": {
            "brand_name": ["Atorvastatin Calcium"],
            "generic_name": ["Atorvastatin"],
            "manufacturer_name": ["Pfizer"],
            "pharm_class_epc": ["HMG-CoA Reductase Inhibitor"],
        },
        "boxed_warning": ["Warning: Skeletal muscle effects."],
        "indications_and_usage": ["Indicated as an adjunct to diet to reduce elevated total-C."],
    }
    parser = FDALabelParser()
    doc = parser.parse(fda_record)

    assert doc.title == "Atorvastatin Calcium (Atorvastatin)"
    assert doc.metadata["boxed_warning_present"] is True
    assert doc.metadata["manufacturer"] == "Pfizer"
    assert len(doc.sections) == 2
    assert doc.sections[0].title == "Boxed Warning"
    assert "Skeletal muscle" in doc.sections[0].content
    assert doc.sections[1].title == "Indications and Usage"
