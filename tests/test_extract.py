from aifa_pipeline.extract import Line, extract_sections, parse_pdf


def section_lines(*texts):
    return [Line(1, text) for text in texts]


def test_numeric_dose_is_not_a_heading():
    result = extract_sections(section_lines("4.2 Posologia", "1.5 mg per day", "4.3 Controindicazioni", "Other text"))
    assert result[0].text == "1.5 mg per day"


def test_major_and_untargeted_sections_end_capture():
    result = extract_sections(section_lines("4.9 Sovradosaggio", "Expected", "5. PROPRIETA FARMACOLOGICHE", "Excluded",
                                          "6.2 Incompatibilita", "Expected too", "6.3 Periodo di validita", "Also excluded"))
    assert [s.text for s in result] == ["Expected", "Expected too"]


def test_wrapped_title_and_pregnancy_alias():
    result = extract_sections(section_lines("4.1", "Indicazioni", "terapeutiche", "Expected", "4.6 Gravidanza e allattamento", "Example"))
    assert [(s.code, s.text) for s in result] == [("4.1", "Expected"), ("4.6", "Example")]


def test_repeated_sections_are_not_merged():
    result = extract_sections([Line(1, "4.1 Indicazioni terapeutiche"), Line(1, "First formulation"),
                               Line(2, "4.1 Indicazioni terapeutiche"), Line(2, "Second formulation")])
    assert [(s.occurrence, s.page_start, s.text) for s in result] == [(1, 1, "First formulation"), (2, 2, "Second formulation")]


def test_unknown_number_does_not_discard_body():
    result = extract_sections(section_lines("4.2 Posologia", "4.10 mg in a synthetic example", "4.3 Controindicazioni", "Text"))
    assert result[0].text.startswith("4.10 mg")


def test_trailing_dot_and_plural_heading_variant():
    result = extract_sections(section_lines("4.5. Interazione con altri medicinali", "First", "4.7 Effetti sulle capacita", "Second"))
    assert [(s.code, s.text) for s in result] == [("4.5", "First"), ("4.7", "Second")]


def test_real_pdf_parsing_and_aic_identity(pdf_bytes):
    result = parse_pdf(pdf_bytes)
    assert result.page_count == 1
    assert result.aics == {"001234567"}
    sections = {s.code: s.text for s in result.sections}
    assert sections["4.2"].startswith("1.5 mg")
    assert sections["4.9"] == "Synthetic overdose text."
    assert sections["6.2"] == "Synthetic incompatibility text."
