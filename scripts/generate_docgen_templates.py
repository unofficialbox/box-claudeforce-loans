#!/usr/bin/env python3
"""Generate Box DocGen-ready LOS Word templates with deterministic styling."""

from pathlib import Path

from docx import Document
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output" / "docgen"
BLUE = "2E74B5"
DARK = "1F4D78"
GRAY = "5F6368"
LIGHT = "F2F4F7"


def set_font(run, size=11, bold=False, color="000000", italic=False):
    run.font.name = "Calibri"
    run._element.get_or_add_rPr().rFonts.set(qn("w:ascii"), "Calibri")
    run._element.get_or_add_rPr().rFonts.set(qn("w:hAnsi"), "Calibri")
    run.font.size = Pt(size)
    run.bold = bold
    run.italic = italic
    run.font.color.rgb = RGBColor.from_string(color)


def shade(cell, fill):
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = tc_pr.find(qn("w:shd"))
    if shd is None:
        shd = OxmlElement("w:shd")
        tc_pr.append(shd)
    shd.set(qn("w:fill"), fill)


def set_cell_margins(cell, top=80, start=120, bottom=80, end=120):
    tc = cell._tc
    tc_pr = tc.get_or_add_tcPr()
    tc_mar = tc_pr.first_child_found_in("w:tcMar")
    if tc_mar is None:
        tc_mar = OxmlElement("w:tcMar")
        tc_pr.append(tc_mar)
    for margin, value in (("top", top), ("start", start), ("bottom", bottom), ("end", end)):
        node = tc_mar.find(qn(f"w:{margin}"))
        if node is None:
            node = OxmlElement(f"w:{margin}")
            tc_mar.append(node)
        node.set(qn("w:w"), str(value))
        node.set(qn("w:type"), "dxa")


def set_table_geometry(table, widths_dxa):
    table.autofit = False
    total = sum(widths_dxa)
    tbl_pr = table._tbl.tblPr
    tbl_w = tbl_pr.find(qn("w:tblW"))
    tbl_w.set(qn("w:w"), str(total))
    tbl_w.set(qn("w:type"), "dxa")
    tbl_ind = tbl_pr.find(qn("w:tblInd"))
    if tbl_ind is None:
        tbl_ind = OxmlElement("w:tblInd")
        tbl_pr.append(tbl_ind)
    tbl_ind.set(qn("w:w"), "120")
    tbl_ind.set(qn("w:type"), "dxa")
    grid = table._tbl.tblGrid
    for child in list(grid):
        grid.remove(child)
    for width in widths_dxa:
        col = OxmlElement("w:gridCol")
        col.set(qn("w:w"), str(width))
        grid.append(col)
    for row in table.rows:
        for idx, cell in enumerate(row.cells):
            tc_pr = cell._tc.get_or_add_tcPr()
            tc_w = tc_pr.find(qn("w:tcW"))
            tc_w.set(qn("w:w"), str(widths_dxa[idx]))
            tc_w.set(qn("w:type"), "dxa")
            set_cell_margins(cell)


def configure(doc, running_label, footer_label="Acme Bank | LOS-2026-Harborview"):
    section = doc.sections[0]
    section.page_width = Inches(8.5)
    section.page_height = Inches(11)
    section.top_margin = Inches(1)
    section.right_margin = Inches(1)
    section.bottom_margin = Inches(1)
    section.left_margin = Inches(1)
    section.header_distance = Inches(0.492)
    section.footer_distance = Inches(0.492)

    normal = doc.styles["Normal"]
    normal.font.name = "Calibri"
    normal.font.size = Pt(11)
    normal._element.rPr.rFonts.set(qn("w:ascii"), "Calibri")
    normal._element.rPr.rFonts.set(qn("w:hAnsi"), "Calibri")
    normal.paragraph_format.space_after = Pt(6)
    normal.paragraph_format.line_spacing = 1.1
    for style_name, size, before, after, color in (
        ("Heading 1", 16, 16, 8, BLUE),
        ("Heading 2", 13, 12, 6, BLUE),
        ("Heading 3", 12, 8, 4, DARK),
    ):
        style = doc.styles[style_name]
        style.font.name = "Calibri"
        style.font.size = Pt(size)
        style.font.bold = True
        style.font.color.rgb = RGBColor.from_string(color)
        style._element.rPr.rFonts.set(qn("w:ascii"), "Calibri")
        style._element.rPr.rFonts.set(qn("w:hAnsi"), "Calibri")
        style.paragraph_format.space_before = Pt(before)
        style.paragraph_format.space_after = Pt(after)

    header = section.header.paragraphs[0]
    header.alignment = WD_ALIGN_PARAGRAPH.LEFT
    header.paragraph_format.space_after = Pt(0)
    set_font(header.add_run(running_label), 9, True, GRAY)
    footer = section.footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    set_font(footer.add_run(footer_label), 8, False, GRAY)


def add_title(doc, kicker, title, subtitle):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(2)
    set_font(p.add_run(kicker.upper()), 9, True, BLUE)
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(4)
    set_font(p.add_run(title), 23, True, "000000")
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(16)
    set_font(p.add_run(subtitle), 12, False, GRAY)


def add_key_values(doc, rows):
    table = doc.add_table(rows=0, cols=2)
    table.style = "Table Grid"
    for label, value in rows:
        cells = table.add_row().cells
        cells[0].vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
        cells[1].vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
        shade(cells[0], LIGHT)
        shade(cells[1], "FFFFFF")
        set_font(cells[0].paragraphs[0].add_run(label), 10, True, DARK)
        set_font(cells[1].paragraphs[0].add_run(value), 10.5)
    set_table_geometry(table, [2700, 6660])
    doc.add_paragraph().paragraph_format.space_after = Pt(0)
    return table


def add_section_text(doc, heading, value):
    doc.add_heading(heading, level=2)
    p = doc.add_paragraph()
    set_font(p.add_run(value), 11)


def term_sheet_markup():
    """The 2026 term sheet still in negotiation: a Word document with the borrower's visible markup (not a merge template)."""
    doc = Document()
    configure(doc, "LOS Term Sheet Markup 2026")
    add_title(
        doc,
        "In negotiation",
        "Term Sheet - Commercial Real Estate Loan - Borrower Markup",
        "Acme Bank and Harborview Logistics Holdings LLC | LOS-2026-Harborview | Draft, with borrower markup",
    )

    def term(heading, body, proposed):
        doc.add_heading(heading, level=2)
        set_font(doc.add_paragraph().add_run(body), 11)
        rp = doc.add_paragraph()
        set_font(rp.add_run("HARBORVIEW MARKUP: " + proposed), 11, bold=True, color="B91C1C")

    term(
        "3. Interest rate",
        "Fixed at 6.85% per annum for the term of the Loan, subject to the Bank's pricing floor of the greater of SOFR plus 2.75% and 6.50%.",
        "Borrower requests relationship pricing of 6.50% in recognition of its existing accounts with the Bank.",
    )
    term(
        "6. Guaranty",
        "Unlimited personal guaranty from each owner of twenty percent or more of the Borrower.",
        "Borrower proposes a limited guaranty from Jordan Pike and Renata Voss capped at $1,000,000 each, and no guaranty from Harborview Employee Holdings LP.",
    )
    doc.add_heading("8. Financial covenants", level=2)
    set_font(
        doc.add_paragraph().add_run(
            "8.1 Loan-to-Value: the outstanding principal shall not exceed 75% of the appraised value of the Collateral, "
            "as determined under Schedule A. 8.2 Debt Service Coverage: not less than 1.25x, calculated and tested in "
            "the manner set out in Section 9.3."
        ),
        11,
    )
    set_font(doc.add_paragraph().add_run("No borrower markup in this section."), 10, italic=True, color=GRAY)
    term(
        "9.3 Financial reporting",
        "Annual reviewed financial statements within 120 days after fiscal year end and quarterly statements within 45 days after each quarter end, each with a compliance certificate calculating the Debt Service Coverage Ratio for the trailing twelve months. The ratio is tested quarterly.",
        "Borrower proposes annual delivery within 180 days after fiscal year end, consistent with the company's audit cycle, with the Debt Service Coverage Ratio calculated for the purposes of Section 8.2 on the annual statements at not less than 1.10x. Quarterly statements and quarterly testing are deleted.",
    )
    term(
        "Schedule A - Collateral",
        "The Real Property at 1200 Harbor Way, its improvements, fixtures, leases and rents. The appraised value for Section 8.1 is the as-is market value stated in the Bank-ordered appraisal. Furniture, trade fixtures, equipment, vehicles and inventory are excluded.",
        "The Collateral also includes all furniture, fixtures and equipment at the Real Property at net book value ($850,000), and that value is included in the appraised value of the Collateral for the purposes of Section 8.1, consistent with the collateral pool under the Borrower's 2025 equipment loan.",
    )
    doc.add_heading("Open items", level=2)
    set_font(
        doc.add_paragraph().add_run(
            "Red text marks the borrower's proposed changes still under negotiation. This document is a draft in Word and is not a commitment to lend."
        ),
        10,
        italic=True,
        color=GRAY,
    )
    return doc


def add_signing_fields(doc):
    """Add fields for recipient 1 using Box Sign's documented tag syntax."""
    signature = doc.add_paragraph()
    signature.paragraph_format.keep_with_next = True
    signature.add_run("Borrower signature\n")
    tag = signature.add_run("[[s|1|id:borrower_signature                    ]]")
    set_font(tag, size=18, color="FFFFFF")
    date = doc.add_paragraph()
    date.add_run("Date signed: ")
    set_font(date.add_run("[[d|1|id:borrower_signed_date]]"), size=10, color="FFFFFF")


def commitment_letter():
    """The document Acme sends once the terms are resolved on the loan record.

    Generating "the loan agreement" is the wrong artifact here -- the definitive documents
    come later, from Loan Documentation. What the bank produces at this point is a
    position: which policy the application is measured against, what the borrower asked
    for, what the standard and the approved exception allow, who owns the exception, and
    what the borrower already agreed to the last two times. Every one of those already
    exists as governed content -- the credit policy library Hub supplies the standard and
    the exception and their owner, the prior executed agreements supply the precedent --
    so this template is the place they are assembled, not the place they are invented.
    """
    doc = Document()
    configure(doc, "LOS Commitment Letter", "Acme Bank | {{loan.id}}")
    add_title(
        doc,
        "Commitment letter",
        "Commitment Letter",
        "Prepared from the credit policy library and prior executed loan agreements",
    )
    add_key_values(doc, [
        ("Loan ID", "{{loan.id}}"),
        ("Borrower", "{{loan.borrower}}"),
        ("Term sheet reference", "{{loan.termSheetReference}}"),
        ("Loan amount", "{{loan.loanAmount}}"),
        ("Status", "{{loan.status}}"),
        ("Prepared", "{{letter.preparedOn}}"),
    ])
    add_section_text(doc, "The policy at issue", "{{terms.policyAtIssue}}")
    add_section_text(doc, "What the borrower requested", "{{terms.requestedPosition}}")
    add_key_values(doc, [
        ("Approved position", "{{terms.approvedPosition}}"),
        ("Approved exception", "{{terms.exceptionPosition}}"),
        ("Exception owner", "{{terms.owner}}"),
        ("Risk", "{{terms.risk}}"),
    ])
    add_section_text(doc, "What the borrower agreed before", "{{precedent.summary}}")
    add_section_text(doc, "Proposed terms", "{{terms.proposedTerms}}")
    add_key_values(doc, [
        ("Prepared by", "{{letter.preparedBy}}"),
        ("Requires approval from", "{{terms.owner}}"),
    ])
    add_section_text(
        doc,
        "Note",
        "This letter is a draft pending Credit Committee approval. It is not a commitment to lend, and it does "
        "not authorise signature or funding. {{terms.owner}} owns the decision on this exception.",
    )
    add_signing_fields(doc)
    return doc


SALESFORCE_TEMPLATE = "los-commitment-letter-salesforce-template.docx"
SF = "LOS_Loan__c"


def sf(field, optional=True):
    """A managed-package tag. The package omits null fields from its payload, and Box prints
    a tag literally when its key is missing, so every field that can be blank on a loan record
    carries `:: optional`. Only identity fields and the loan amount are required."""
    return "{{" + SF + "." + field + (" :: optional" if optional else "") + "}}"


def commitment_letter_salesforce():
    """The commitment letter merged by Box Doc Gen for Salesforce from the loan record itself.

    The first template is filled by the presenter's assistant with a hand-built payload
    (`loan.*`, `terms.*`, `precedent.*`, `letter.*`). This one is filled by the Box for
    Salesforce managed package: an admin registers it on the Box Doc Gen Templates tab
    against `LOS_Loan__c`, and every tag is a path into the `LOS_Loan__cDocGen.json` that
    tab exports (`sample-data/docgen/LOS_Loan__c_DocGen.json`). Tags name Salesforce API
    fields (`{{LOS_Loan__c.Loan_ID__c}}`) and walk lookups through `__r` relationships.

    Verified against the package's preview and a direct Box Doc Gen run: a null field is
    omitted from the payload and its tag prints literally unless marked `:: optional`; an
    empty string renders blank; `$User` is not resolved by Box even when supplied; and the
    package does not send a lookup's child list (`Borrower_Account__r.Borrower_Loans__r`),
    so this template has no tablerow. It carries the same Box Sign fields as the first
    template so `prepareSignatureRequest` works on its output.
    """
    doc = Document()
    configure(doc, "LOS Commitment Letter (Salesforce)", "Acme Bank | " + sf("Loan_ID__c", optional=False))
    add_title(
        doc,
        "Commitment letter",
        "Commitment Letter",
        "Generated by Box Doc Gen for Salesforce from loan record " + sf("Name", optional=False),
    )
    add_key_values(doc, [
        ("Loan ID", sf("Loan_ID__c", optional=False)),
        ("Borrower", sf("Borrower__c")),
        ("Borrower entity", sf("Borrower_Entity__c")),
        ("Borrower account", sf("Borrower_Account__r.Name")),
        ("Loan type", sf("Loan_Type__c")),
        ("Purpose", sf("Purpose__c")),
        ("Region", sf("Region__c")),
        ("Status", sf("Status__c", optional=False)),
        ("Loan officer", sf("Loan_Officer_Name__c")),
    ])
    doc.add_heading("Credit terms", level=2)
    add_key_values(doc, [
        ("Loan amount", "USD {{" + SF + ".Loan_Amount__c :: format(\"US-Number\")}}"),
        ("Interest rate (% per annum)", sf("Interest_Rate__c")),
        ("Term (months)", sf("Term_Months__c")),
        ("Loan-to-value (%)", sf("LTV__c")),
        ("Debt service coverage (x)", sf("DSCR__c")),
        ("Collateral", sf("Collateral_Type__c")),
        ("Collateral value (USD)", sf("Collateral_Value__c")),
        ("Target closing date", sf("Target_Closing_Date__c")),
        ("Maturity date", sf("Maturity_Date__c")),
        ("Risk rating", sf("Risk_Rating__c")),
    ])
    doc.add_heading("Underwriting notes", level=2)
    set_font(doc.add_paragraph().add_run("{{ if " + SF + ".Underwriting_Notes__c isPresent }}"), 11)
    set_font(doc.add_paragraph().add_run(sf("Underwriting_Notes__c", optional=False)), 11)
    set_font(doc.add_paragraph().add_run("{{ else }}"), 11)
    set_font(doc.add_paragraph().add_run("No underwriting notes are recorded on the loan record."), 11)
    set_font(doc.add_paragraph().add_run("{{ endif }}"), 11)
    doc.add_heading("Borrower relationship", level=2)
    add_key_values(doc, [
        ("Applicant", sf("Applicant_Name__c")),
        ("Applicant email", sf("Applicant_Email__c")),
        ("Industry", sf("Borrower_Account__r.Industry")),
        ("Billing street", sf("Borrower_Account__r.BillingStreet")),
        ("Billing city", sf("Borrower_Account__r.BillingCity")),
        ("Billing state and postal code", sf("Borrower_Account__r.BillingState") + " " + sf("Borrower_Account__r.BillingPostalCode")),
        ("Opportunity", sf("Opportunity__r.Name")),
        ("Opportunity stage", sf("Opportunity__r.StageName")),
    ])
    doc.add_heading("Prepared by", level=2)
    add_key_values(doc, [
        ("Loan officer", sf("Loan_Officer__r.Name")),
        ("Title", sf("Loan_Officer__r.Title")),
        ("Email", sf("Loan_Officer__r.Email")),
        ("Phone", sf("Loan_Officer__r.Phone")),
    ])
    add_section_text(
        doc,
        "Note",
        "This letter is generated from the Salesforce loan record and is a draft pending Credit Committee approval. "
        "It is not a commitment to lend, and it does not authorise signature or funding until the loan record "
        "reaches an approved status.",
    )
    add_signing_fields(doc)
    return doc


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    templates = {
        "los-commitment-letter-template.docx": commitment_letter(),
        SALESFORCE_TEMPLATE: commitment_letter_salesforce(),
        "harborview-term-sheet-2026-markup.docx": term_sheet_markup(),
    }
    for name, document in templates.items():
        document.core_properties.title = name.removesuffix(".docx").replace("-", " ").title()
        document.core_properties.subject = "Box DocGen template for the Harborview LOS demo"
        document.core_properties.author = "Acme Bank LOS Demo"
        document.save(OUTPUT / name)
        print(OUTPUT / name)


if __name__ == "__main__":
    main()
