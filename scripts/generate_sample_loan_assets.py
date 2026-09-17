from __future__ import annotations

import json
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
PDF_OUT = ROOT / "output" / "pdf"
JSON_OUT = ROOT / "output" / "json"
# Reserved for tabular fixtures; the validator rebinds it alongside PDF_OUT and JSON_OUT.
CSV_OUT = ROOT / "output" / "csv"
for directory in (PDF_OUT, JSON_OUT):
    directory.mkdir(parents=True, exist_ok=True)


styles = getSampleStyleSheet()
styles.add(
    ParagraphStyle(
        name="DocTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#172554"),
        spaceAfter=8,
    )
)
styles.add(
    ParagraphStyle(
        name="DocSubTitle",
        parent=styles["BodyText"],
        fontSize=9,
        leading=12,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#475569"),
        spaceAfter=12,
    )
)
styles.add(
    ParagraphStyle(
        name="SectionTitle",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=14,
        textColor=colors.HexColor("#075985"),
        spaceBefore=11,
        spaceAfter=5,
    )
)
styles.add(
    ParagraphStyle(
        name="Body",
        parent=styles["BodyText"],
        fontSize=9,
        leading=12,
        alignment=TA_LEFT,
    )
)
styles.add(
    ParagraphStyle(
        name="Small",
        parent=styles["BodyText"],
        fontSize=7.5,
        leading=9,
        textColor=colors.HexColor("#64748b"),
    )
)


def footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(colors.HexColor("#64748b"))
    canvas.drawString(0.65 * inch, 0.43 * inch, "Synthetic loan origination demo artifact - not financial or legal advice")
    canvas.drawRightString(7.85 * inch, 0.43 * inch, f"Page {doc.page}")
    canvas.restoreState()


def make_doc(path: Path):
    doc = BaseDocTemplate(
        str(path),
        pagesize=LETTER,
        rightMargin=0.65 * inch,
        leftMargin=0.65 * inch,
        topMargin=0.6 * inch,
        bottomMargin=0.65 * inch,
    )
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="main")
    doc.addPageTemplates([PageTemplate(id="template", frames=[frame], onPage=footer)])
    return doc


def p(text: str, style: str = "Body"):
    return Paragraph(text, styles[style])


def section(title: str):
    return p(title, "SectionTitle")


def markup(text: str):
    """The borrower's proposed change, in red, the way a marked-up term sheet reads."""
    return p(f"<font color='#b91c1c'><b>HARBORVIEW MARKUP:</b> {text}</font>")


def table(rows, widths=None, header=True):
    processed = []
    for row in rows:
        processed.append([cell if hasattr(cell, "wrap") else p(str(cell), "Body") for cell in row])
    tbl = Table(processed, colWidths=widths, hAlign="LEFT", repeatRows=1 if header else 0)
    style = [
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#e2e8f0")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]
    if header:
        style.extend(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e0f2fe")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
            ]
        )
    tbl.setStyle(TableStyle(style))
    return tbl


def doc_header(title: str, subtitle: str):
    return [p(title, "DocTitle"), p(subtitle, "DocSubTitle"), Spacer(1, 0.12 * inch)]


def synthetic_note(kind: str):
    return p(
        f"This synthetic {kind} is designed for loan origination demonstrations. Names, addresses, "
        "amounts, and terms are fictional and are not financial or legal advice.",
        "Small",
    )


BANK = "Acme Bank"
BANK_ADDRESS = "200 Commerce Street, Suite 900, Boston, Massachusetts 02109"
BORROWER_2026 = "Harborview Logistics Holdings LLC"
PROPERTY = "1200 Harbor Way, Everett, Massachusetts 02149"


# --------------------------------------------------------------------------------------
# 2026 application package
# --------------------------------------------------------------------------------------


def build_loan_application():
    """The borrower's own summary of the request, exactly as it arrived.

    Every number here is the borrower's: the $6,000,000 collateral value is a broker
    opinion from 2024, not an appraisal, and the resulting 80% loan-to-value is what the
    borrower believes it is asking for. The bank-ordered appraisal (build_appraisal) is
    what turns 80% into 85%, so this document has to state the borrower's figure plainly
    rather than the corrected one.
    """
    path = PDF_OUT / "harborview-loan-application-2026.pdf"
    story = doc_header(
        "Commercial Loan Application - Summary",
        f"{BORROWER_2026} | Distribution Facility Acquisition | Received by {BANK} | LOS-2026-Harborview",
    )
    story += [
        section("1. Applicant"),
        table(
            [
                ["Field", "Value"],
                ["Borrowing entity", BORROWER_2026],
                ["Parent / operating company", "Harborview Logistics (Transportation and third-party logistics)"],
                ["Principal place of business", "48 Pier Road, Everett, Massachusetts 02149"],
                ["Primary contact", "Dana Whitfield, Chief Financial Officer, dana.whitfield@harborviewlogistics.example"],
                ["Years in operation", "14"],
                ["Existing relationship", "Revolving line of credit (2023) and equipment term loan (2025), both current"],
            ],
            widths=[2.1 * inch, 4.8 * inch],
        ),
        section("2. Request"),
        table(
            [
                ["Term requested", "Borrower position"],
                ["Loan amount", "$4,800,000"],
                ["Loan type", "Commercial real estate - owner-occupied acquisition"],
                ["Purpose", f"Acquire the distribution facility at {PROPERTY} (purchase price $6,000,000)"],
                ["Requested term", "120 months"],
                ["Requested amortization", "25 years"],
                ["Requested interest rate", "6.85% fixed"],
                ["Borrower-stated collateral value", "$6,000,000 (broker opinion of value, March 2024)"],
                ["Borrower-stated loan-to-value", "80%"],
                ["Equity contribution", "$1,200,000 cash at closing"],
                ["Requested closing", "November 30, 2026"],
            ],
            widths=[2.1 * inch, 4.8 * inch],
        ),
        section("3. Ownership and Guarantors"),
        table(
            [
                ["Owner", "Ownership", "Guaranty offered"],
                ["Dana Whitfield", "35%", "Personal guaranty"],
                ["Renata Voss", "35%", "Personal guaranty"],
                ["Harborview Employee Holdings LP", "30%", "None proposed"],
            ],
            widths=[2.6 * inch, 1.4 * inch, 2.9 * inch],
        ),
        section("4. Sources and Uses"),
        table(
            [
                ["Sources", "Amount", "Uses", "Amount"],
                ["Acme Bank loan", "$4,800,000", "Purchase price", "$6,000,000"],
                ["Borrower equity", "$1,200,000", "Closing costs and reserves", "$0 (borrower-paid outside closing)"],
                ["Total", "$6,000,000", "Total", "$6,000,000"],
            ],
            widths=[1.75 * inch, 1.3 * inch, 2.35 * inch, 1.5 * inch],
        ),
        section("5. Documents Submitted with this Application"),
        p(
            "FY2025 financial statements (reviewed), 2025 federal tax return summary, business bank "
            "statements for April through June 2026, certificate of insurance, Phase I environmental "
            "site assessment, and the Borrower's marked-up copy of the Bank's term sheet."
        ),
        section("6. Applicant Certification"),
        p(
            "The undersigned certifies that the information in this application is true and complete "
            "and authorizes the Bank to obtain credit reports, appraisals, and other information "
            "required to evaluate the request. Signed: /s/ Dana Whitfield, Chief Financial Officer, "
            "July 8, 2026."
        ),
        Spacer(1, 0.2 * inch),
        synthetic_note("loan application"),
    ]
    make_doc(path).build(story)
    return path


def loan_agreement_sections(*, executed: bool, ltv_pct: int, dscr: str, reporting: str):
    """Sections 1-12 of Acme's form of loan agreement.

    The term sheet and both executed agreements are built from this one list so the
    section numbers are identical across all three documents. That is what lets a reader
    put 9.3 beside 9.3 and Schedule A beside Schedule A, which is the whole point of the
    precedent finding.
    """
    past = executed
    return [
        (
            "8. FINANCIAL COVENANTS",
            [
                f"8.1 <b>Loan-to-Value.</b> The outstanding principal balance of the Loan {'did' if past else 'shall'} not "
                f"at any time exceed {ltv_pct}% of the appraised value of the Collateral, as determined under "
                "Schedule A and by an appraisal ordered by the Bank.",
                f"8.2 <b>Debt Service Coverage.</b> Borrower {'maintained' if past else 'shall maintain'} a Debt Service "
                f"Coverage Ratio of not less than {dscr}, calculated and tested in the manner set out in "
                "Section 9.3.",
            ],
        ),
        (
            "9. REPORTING AND INSPECTION",
            [
                f"9.1 <b>Notices.</b> Borrower {'gave' if past else 'shall give'} the Bank prompt written notice of any "
                "Event of Default, any material litigation, and any change in ownership of more than ten percent.",
                f"9.2 <b>Inspection.</b> The Bank {'was' if past else 'shall be'} entitled to inspect the Collateral and "
                "Borrower's books and records on reasonable notice during business hours.",
                f"9.3 <b>Financial Reporting.</b> {reporting}",
            ],
        ),
    ]


def build_term_sheet_markup():
    """Acme's term sheet, returned by the borrower with its markup in red.

    The point of this document is that the risk is not where anyone would look for it.
    Section 8, the one titled "Financial Covenants", is untouched: it still reads 75% and
    1.25x, and a reviewer who checks that section signs off. The debt service test is
    weakened one section later, in 9.3 "Financial Reporting", by moving the test from
    quarterly to annual and restating the threshold to 1.10x inside the reporting
    mechanics. The loan-to-value is inflated at the other end of the document, in
    Schedule A "Collateral", by adding furniture, fixtures and equipment to the collateral
    pool at book value so that the same $4.8M reads as 70% instead of 85%.

    A keyword search for "loan-to-value" returns nothing in the markup. Only reading the
    document against the credit policy library does.
    """
    path = PDF_OUT / "harborview-term-sheet-2026-borrower-markup.pdf"
    reporting = (
        "Borrower shall deliver to the Bank (a) annual financial statements reviewed by an independent "
        "accountant within 120 days after each fiscal year end and (b) quarterly financial statements within "
        "45 days after each fiscal quarter end, together with a compliance certificate calculating the Debt "
        "Service Coverage Ratio for the trailing twelve months. The Debt Service Coverage Ratio is tested "
        "quarterly on the basis of each compliance certificate."
    )
    sections = loan_agreement_sections(executed=False, ltv_pct=75, dscr="1.25x", reporting=reporting)
    story = doc_header(
        "Term Sheet - Commercial Real Estate Loan (Borrower Markup)",
        f"{BANK} and {BORROWER_2026} | Term sheet dated July 21, 2026 | LOS-2026-Harborview",
    )
    story += [
        p(
            f"This term sheet summarises the terms on which {BANK}, {BANK_ADDRESS} (the <b>Bank</b>), would "
            f"consider extending a loan to {BORROWER_2026} (the <b>Borrower</b>). It is not a commitment to lend. "
            "A commitment, if issued, will be subject to Credit Committee approval and definitive loan documents "
            "on the Bank's standard form."
        ),
        p(
            "<i>Section numbering follows the Bank's form of loan agreement so that each term can be read beside "
            "the corresponding section of the Borrower's executed 2023 and 2025 agreements. Borrower's proposed "
            "changes are shown in red and remain subject to Credit Risk review.</i>"
        ),
        section("1. PARTIES"),
        p(f"Lender: {BANK}. Borrower: {BORROWER_2026}, a Massachusetts limited liability company and wholly "
          "owned subsidiary of Harborview Logistics. Guarantors: as set out in Section 6."),
        section("2. LOAN AMOUNT AND PURPOSE"),
        p(f"2.1 A term loan of up to $4,800,000 (the <b>Loan</b>) to finance the acquisition of the distribution "
          f"facility at {PROPERTY} (the <b>Real Property</b>) for owner occupancy."),
        p("2.2 Borrower shall contribute cash equity of not less than $1,200,000 at closing."),
        section("3. INTEREST RATE"),
        p("3.1 Fixed at 6.85% per annum for the term of the Loan, subject to the Bank's pricing floor of the "
          "greater of SOFR plus 2.75% and 6.50%."),
        markup("Borrower requests relationship pricing of 6.50% in recognition of its existing accounts with the Bank."),
        section("4. TERM, AMORTIZATION AND MATURITY"),
        p("4.1 Term: 120 months from closing. 4.2 Amortization: 25 years, with monthly payments of principal and "
          "interest. 4.3 All outstanding principal and accrued interest is due at maturity."),
        section("5. COLLATERAL AND SECURITY"),
        p("5.1 A first-priority mortgage on the Real Property and a first-priority security interest in the other "
          "Collateral described in Schedule A. 5.2 The appraised value of the Collateral is determined by an "
          "appraisal ordered by the Bank from an approved appraiser. 5.3 Borrower shall maintain property, "
          "general liability, and flood insurance naming the Bank as mortgagee and loss payee."),
        section("6. GUARANTY"),
        p("6.1 Unlimited personal guaranty from each owner of twenty percent or more of the Borrower."),
        markup("Borrower proposes a limited guaranty from Dana Whitfield and Renata Voss capped at $1,000,000 each, "
               "and no guaranty from Harborview Employee Holdings LP."),
        section("7. CONDITIONS PRECEDENT"),
        p("Satisfactory appraisal, title insurance, survey, Phase I environmental site assessment, evidence of "
          "insurance, formation documents, and executed loan documents."),
        PageBreak(),
    ]
    for title, paragraphs in sections:
        story.append(section(title))
        story.extend(p(text) for text in paragraphs)
        if title.startswith("9."):
            story.append(
                markup(
                    "Borrower proposes that the financial statements and compliance certificate in this Section be "
                    "delivered annually, within 180 days after each fiscal year end, consistent with the company's "
                    "audit cycle, and that the Debt Service Coverage Ratio be calculated for the purposes of Section "
                    "8.2 on the basis of the annual statements at not less than 1.10x. Quarterly statements and "
                    "quarterly testing are deleted."
                )
            )
    story += [
        section("10. EVENTS OF DEFAULT"),
        p("Non-payment, breach of a covenant in Section 8 or 9 not cured within thirty days, misrepresentation, "
          "cross-default to other indebtedness of the Borrower or a Guarantor to the Bank, and insolvency."),
        section("11. FEES AND EXPENSES"),
        p("Origination fee of 0.50% of the Loan amount. Borrower pays the Bank's appraisal, environmental, title, "
          "and legal costs whether or not the Loan closes."),
        section("12. GOVERNING LAW"),
        p("The Commonwealth of Massachusetts."),
        section("SCHEDULE A - COLLATERAL"),
        p("The Collateral consists of the Real Property, all improvements and fixtures forming part of the Real "
          "Property, the leases and rents of the Real Property, and the proceeds of each. The appraised value of "
          "the Collateral for the purposes of Section 8.1 is the as-is market value of the Real Property stated in "
          "the Bank-ordered appraisal. Furniture, trade fixtures, equipment, vehicles, and inventory are excluded."),
        markup(
            "The Collateral also includes all furniture, fixtures and equipment located at the Real Property, "
            "valued at net book value per the Borrower's most recent balance sheet ($850,000), and that value is "
            "included in the appraised value of the Collateral for the purposes of Section 8.1, consistent with "
            "the collateral pool under the Borrower's 2025 equipment loan."
        ),
        section("SCHEDULE 1 - NEGOTIATED COVENANTS"),
        p("To be agreed. The Borrower's executed 2023 and 2025 agreements each carry a Schedule 1.", "Small"),
        section("BORROWER MARGIN NOTES - FOR CREDIT RISK REVIEW"),
        table(
            [
                ["Section", "Borrower position"],
                ["3.1", "Relationship pricing at 6.50%."],
                ["6.1", "Limited guaranty, capped at $1,000,000 per individual; no guaranty from the employee holding entity."],
                ["9.3", "Annual reporting and testing, aligned to the audit cycle. Administrative alignment only."],
                ["Schedule A", "Include FF&E in the collateral description, consistent with the 2025 equipment loan."],
            ],
            widths=[1.1 * inch, 5.4 * inch],
        ),
        p("<i>Status: with Credit Risk. No Bank response issued as at the date of this markup.</i>"),
        Spacer(1, 0.2 * inch),
        synthetic_note("term sheet"),
    ]
    make_doc(path).build(story)
    return path


def build_financial_statements():
    path = PDF_OUT / "harborview-financial-statements-fy2025.pdf"
    story = doc_header(
        "Financial Statements - Fiscal Year 2025",
        "Harborview Logistics and subsidiaries | Reviewed, not audited | Year ended December 31, 2025",
    )
    story += [
        section("Income Statement"),
        table(
            [
                ["Line", "FY2025", "FY2024"],
                ["Freight and logistics revenue", "$18,450,000", "$16,920,000"],
                ["Cost of services", "$(13,610,000)", "$(12,380,000)"],
                ["Gross profit", "$4,840,000", "$4,540,000"],
                ["Selling, general and administrative", "$(3,265,000)", "$(2,980,000)"],
                ["Depreciation and amortization", "$(612,000)", "$(548,000)"],
                ["Operating income", "$963,000", "$1,012,000"],
                ["Interest expense (existing facilities)", "$(258,000)", "$(196,000)"],
                ["Net income before tax", "$705,000", "$816,000"],
            ],
            widths=[3.3 * inch, 1.8 * inch, 1.8 * inch],
        ),
        section("Balance Sheet (December 31, 2025)"),
        table(
            [
                ["Assets", "Amount", "Liabilities and Equity", "Amount"],
                ["Cash", "$412,000", "Accounts payable", "$1,180,000"],
                ["Accounts receivable, net", "$2,240,000", "Revolving line of credit (2023)", "$1,150,000"],
                ["Property and equipment, net", "$3,905,000", "Equipment term loan (2025)", "$1,935,000"],
                ["Furniture, fixtures and equipment, net", "$850,000", "Other liabilities", "$372,000"],
                ["Other assets", "$296,000", "Members' equity", "$3,066,000"],
                ["Total assets", "$7,703,000", "Total liabilities and equity", "$7,703,000"],
            ],
            widths=[2.2 * inch, 1.2 * inch, 2.3 * inch, 1.2 * inch],
        ),
        section("Debt Service Coverage - Proposed Facility Loan"),
        p(
            "Prepared by the Borrower for the Bank's underwriting. Net operating income available for debt "
            "service on the proposed distribution facility loan is calculated after existing debt service on "
            "the 2023 and 2025 facilities."
        ),
        table(
            [
                ["Measure", "FY2025"],
                ["Net operating income available for debt service", "$448,000"],
                ["Proposed annual debt service ($4,800,000 at 6.85%, 25-year amortization)", "$400,000"],
                ["Debt Service Coverage Ratio", "1.12x"],
            ],
            widths=[4.9 * inch, 2.0 * inch],
        ),
        section("Notes"),
        p("Note 1. Revenue is recognised when freight is delivered. Note 2. Furniture, fixtures and equipment are "
          "carried at cost less accumulated depreciation; the net book value of $850,000 relates to racking, "
          "conveyors, and office fit-out at the leased Pier Road facility. Note 3. The Borrower has not been "
          "audited; these statements were reviewed by Beacon and Lowell CPAs."),
        Spacer(1, 0.2 * inch),
        synthetic_note("financial statement"),
    ]
    make_doc(path).build(story)
    return path


def build_tax_return_summary():
    path = PDF_OUT / "harborview-tax-return-summary-2025.pdf"
    story = doc_header(
        "Federal Tax Return Summary - Tax Year 2025",
        "Harborview Logistics | Form 1120-S summary prepared for lender review | Not a filed return",
    )
    story += [
        table(
            [
                ["Line", "Amount"],
                ["Gross receipts or sales", "$18,450,000"],
                ["Cost of goods sold", "$13,610,000"],
                ["Total income", "$4,840,000"],
                ["Total deductions", "$4,135,000"],
                ["Ordinary business income", "$705,000"],
                ["Depreciation (Form 4562)", "$612,000"],
                ["Interest expense", "$258,000"],
                ["Officer compensation", "$540,000"],
            ],
            widths=[3.9 * inch, 2.4 * inch],
        ),
        section("Shareholder Information"),
        table(
            [
                ["Shareholder", "Ownership", "Pro rata share of ordinary income"],
                ["Dana Whitfield", "35%", "$246,750"],
                ["Renata Voss", "35%", "$246,750"],
                ["Harborview Employee Holdings LP", "30%", "$211,500"],
            ],
            widths=[2.6 * inch, 1.3 * inch, 3.0 * inch],
        ),
        section("Reconciliation to Financial Statements"),
        p("Ordinary business income agrees to net income before tax in the FY2025 reviewed financial statements. "
          "No book-to-tax differences were reported other than timing of depreciation."),
        Spacer(1, 0.2 * inch),
        synthetic_note("tax return summary"),
    ]
    make_doc(path).build(story)
    return path


def build_bank_statements():
    """Three months of operating account activity.

    The average balance matters for one policy decision: relationship pricing (LOS-RATE-002)
    requires $500,000 or more in operating deposits, and the borrower asks for it in the
    term sheet markup. The statements show roughly $310,000, so the request fails on the
    borrower's own evidence.
    """
    path = PDF_OUT / "harborview-bank-statements-q2-2026.pdf"
    story = doc_header(
        "Business Operating Account Statements - April to June 2026",
        "Harborview Logistics | Operating account summary prepared for lender review",
    )
    story += [
        table(
            [
                ["Month", "Opening balance", "Deposits", "Withdrawals", "Closing balance", "Average daily balance"],
                ["April 2026", "$298,400", "$1,562,300", "$1,541,900", "$318,800", "$304,600"],
                ["May 2026", "$318,800", "$1,498,700", "$1,522,400", "$295,100", "$309,200"],
                ["June 2026", "$295,100", "$1,631,900", "$1,596,200", "$330,800", "$316,400"],
            ],
            widths=[0.95 * inch, 1.1 * inch, 1.05 * inch, 1.05 * inch, 1.1 * inch, 1.65 * inch],
        ),
        section("Observations"),
        p("Three-month average daily balance: $310,067. No overdrafts, returned items, or non-sufficient-funds "
          "events in the period. Recurring debits include payroll, fuel, the 2023 line of credit interest, and the "
          "2025 equipment loan payment of $42,500 per month."),
        Spacer(1, 0.2 * inch),
        synthetic_note("bank statement summary"),
    ]
    make_doc(path).build(story)
    return path


def build_appraisal():
    """The bank-ordered appraisal, and the number the whole story turns on.

    The borrower stated $6,000,000. The appraiser reconciles to $5,650,000, which puts
    $4,800,000 at 85% loan-to-value against a 75% policy maximum and an 80% approved
    exception. The report also says, in plain words, that FF&E is excluded from the real
    property value, which is what the Schedule A markup quietly reverses.
    """
    path = PDF_OUT / "harborview-appraisal-2026.pdf"
    story = doc_header(
        "Appraisal Report - Industrial Distribution Facility",
        f"{PROPERTY} | Prepared for {BANK} | Effective date August 4, 2026 | Meridian Valuation Group",
    )
    story += [
        section("1. Summary of Salient Facts"),
        table(
            [
                ["Item", "Finding"],
                ["Property type", "Single-tenant industrial distribution facility, 118,000 square feet on 9.2 acres"],
                ["Intended use", "Mortgage lending; owner-occupied acquisition financing"],
                ["Interest appraised", "Fee simple, as-is"],
                ["Highest and best use", "Continued use as a distribution facility"],
                ["Borrower-stated value", "$6,000,000 (broker opinion of value, March 2024; not an appraisal)"],
                ["Appraised value, as-is", "$5,650,000"],
                ["Proposed loan amount", "$4,800,000"],
                ["Loan-to-value at appraised value", "85%"],
            ],
            widths=[2.1 * inch, 4.8 * inch],
        ),
        section("2. Valuation Approaches"),
        table(
            [
                ["Approach", "Indicated value", "Weight"],
                ["Sales comparison (five improved sales, 2024-2026)", "$5,600,000", "Primary"],
                ["Income capitalization (market rent $9.10 per square foot, 7.25% cap rate)", "$5,700,000", "Secondary"],
                ["Cost approach (replacement cost less depreciation plus land)", "$5,900,000", "Support only"],
                ["Reconciled as-is market value", "$5,650,000", ""],
            ],
            widths=[4.2 * inch, 1.5 * inch, 1.2 * inch],
        ),
        section("3. Reconciliation"),
        p("The 2024 broker opinion relied on two sales that have since re-traded at lower prices and assumed "
          "a cap rate of 6.50%. Current market evidence supports 7.25%. The reconciled value places most weight on "
          "the sales comparison approach, supported by the income approach."),
        section("4. Personal Property"),
        p("<b>Furniture, fixtures, equipment, racking, and conveyors are personal property and are excluded from "
          "the real property value stated in this report.</b> No value is assigned to them. Any lender wishing to "
          "rely on personal property as collateral should obtain a separate equipment appraisal."),
        section("5. Certification"),
        p("The appraiser certifies that the statements of fact are true, the analyses are limited only by the "
          "stated assumptions, and the appraiser has no present or prospective interest in the property. "
          "Signed: /s/ T. Okonkwo, MAI, Massachusetts Certified General Real Estate Appraiser."),
        Spacer(1, 0.2 * inch),
        synthetic_note("appraisal report"),
    ]
    make_doc(path).build(story)
    return path


def build_insurance():
    path = PDF_OUT / "harborview-insurance-certificate.pdf"
    story = doc_header(
        "Certificate of Insurance",
        f"Insured: {BORROWER_2026} | Certificate holder and mortgagee: {BANK} | LOS-2026-Harborview",
    )
    story += [
        table(
            [
                ["Coverage", "Limit", "Carrier", "Expiration"],
                ["Property (replacement cost, special form)", "$6,500,000", "Beacon Mutual Insurance", "2027-06-30"],
                ["Commercial General Liability", "$2,000,000 per occurrence", "Beacon Mutual Insurance", "2027-06-30"],
                ["Flood (NFIP, Zone AE)", "$500,000 building", "National Flood Program", "2027-06-30"],
            ],
            widths=[2.5 * inch, 1.6 * inch, 1.6 * inch, 1.2 * inch],
        ),
        section("Mortgagee and Loss Payee"),
        p(f"{BANK}, its successors and assigns, {BANK_ADDRESS}, is named as mortgagee and loss payee on the "
          "property and flood policies and as additional insured on the general liability policy."),
        section("Demo Covenant"),
        p("Create an insurance renewal reminder ninety days before certificate expiration and assign it to "
          "Portfolio Management (covenant type: Insurance Renewal)."),
        Spacer(1, 0.2 * inch),
        synthetic_note("certificate of insurance"),
    ]
    make_doc(path).build(story)
    return path


def build_environmental_report():
    path = PDF_OUT / "harborview-environmental-report-2026.pdf"
    story = doc_header(
        "Phase I Environmental Site Assessment - Executive Summary",
        f"{PROPERTY} | Prepared for {BANK} | July 29, 2026 | Northbank Environmental Consultants",
    )
    story += [
        section("1. Purpose and Scope"),
        p("This assessment was performed in accordance with ASTM E1527-21 to identify recognized environmental "
          "conditions in connection with the acquisition financing of the property. The scope included a site "
          "reconnaissance, interviews, a review of historical sources and regulatory databases, and a review of "
          "prior reports."),
        section("2. Findings"),
        table(
            [
                ["Area", "Finding"],
                ["Recognized environmental conditions", "None identified"],
                ["Historical recognized environmental conditions", "None identified"],
                ["Controlled recognized environmental conditions", "None identified"],
                ["De minimis conditions", "Minor staining at the truck fueling pad; housekeeping item only"],
                ["Regulatory database listings", "Property not listed; one closed leaking underground storage tank site 0.4 miles east, downgradient"],
            ],
            widths=[2.6 * inch, 4.3 * inch],
        ),
        section("3. Conclusions and Recommendations"),
        p("No recognized environmental conditions were identified. No further investigation is recommended. "
          "The consultant recommends routine maintenance of the fueling pad and confirmation that the current "
          "spill prevention plan remains on file."),
        Spacer(1, 0.2 * inch),
        synthetic_note("environmental report"),
    ]
    make_doc(path).build(story)
    return path


# --------------------------------------------------------------------------------------
# Prior executed loan agreements
# --------------------------------------------------------------------------------------


def build_executed_loan_agreement(
    *,
    year: int,
    loan_id: str,
    facility: str,
    facility_title: str,
    amount: str,
    term_months: int,
    rate: str,
    collateral: str,
    collateral_value: str,
    dscr_actual: str,
    maturity: str,
    signed_on: str,
    borrower: str,
    prior_year: int | None = None,
):
    """A prior Harborview loan agreement, executed, on Acme's own form.

    These two documents exist to make one point that a single term sheet cannot make: the
    2026 markup is not asking the bank for something new. It is asking the bank to give
    back two positions Harborview already accepted, in writing, twice.

    Both prior agreements carry a negotiated Schedule 1: loan-to-value tightened from the
    75% standard to 70%, and debt service coverage tightened from 1.25x to 1.30x tested
    quarterly. The 2026 markup regresses both, and does so in sections that are not the
    ones titled "Financial Covenants". So the finding is not "this is off policy"; it is
    "the borrower is walking back covenants it agreed to twice", which is a different and
    much better conversation to hand to Credit Risk.

    The section numbers are deliberately identical across all three documents, so the
    reader can put 9.3 beside 9.3 and Schedule A beside Schedule A and see it.
    """
    path = PDF_OUT / f"harborview-loan-agreement-{year}-executed.pdf"
    renewal = prior_year is not None
    reporting = (
        "Borrower delivered annual reviewed financial statements within 120 days after each fiscal year end "
        "and quarterly financial statements within 45 days after each fiscal quarter end, each accompanied by "
        "a compliance certificate calculating the Debt Service Coverage Ratio for the trailing twelve months. "
        "<b>As amended</b>, the Debt Service Coverage Ratio was tested quarterly on the basis of each "
        "compliance certificate against the 1.30x threshold in Schedule 1."
    )
    sections = loan_agreement_sections(executed=True, ltv_pct=70, dscr="1.30x", reporting=reporting)
    story = doc_header(
        f"{facility_title} - Executed {year}",
        f"{BANK} and {borrower} | Loan {loan_id} | Executed {signed_on} | LOS-{year}-Harborview",
    )
    story += [
        p(
            f"THIS LOAN AGREEMENT was made on {signed_on} BETWEEN {BANK}, {BANK_ADDRESS} (the <b>Bank</b>) and "
            f"{borrower} (the <b>Borrower</b>). This Agreement was executed by the parties and is in full force "
            "and effect."
            + (
                f" It was negotiated alongside the {prior_year} revolving line of credit, and the covenants "
                f"recorded in Schedule 1 of that agreement were carried forward unchanged."
                if renewal
                else ""
            )
        ),
        p(
            "<i>Drafted on the Bank's standard form. The departures from the standard form at Sections 8.1, 8.2 "
            "and 9.3 and at Schedule A were agreed with Credit Risk during negotiation and are recorded in "
            "Schedule 1.</i>"
        ),
        section("1. PARTIES"),
        p(f"Lender: {BANK}. Borrower: {borrower}. Guarantors: Dana Whitfield and Renata Voss, jointly and severally, "
          "under unlimited personal guaranties."),
        section("2. LOAN AMOUNT AND PURPOSE"),
        p(f"2.1 {facility} in the principal amount of {amount} (the <b>Loan</b>)."),
        section("3. INTEREST RATE"),
        p(f"3.1 {rate}."),
        section("4. TERM, AMORTIZATION AND MATURITY"),
        p(f"4.1 Term: {term_months} months from closing. 4.2 Maturity date: {maturity}, on which all outstanding "
          "principal and accrued interest is due."),
        section("5. COLLATERAL AND SECURITY"),
        p(f"5.1 A first-priority security interest in the Collateral described in Schedule A. 5.2 The value of "
          f"the Collateral for the purposes of Section 8.1 was established at {collateral_value} by a valuation "
          "ordered by the Bank."),
        section("6. GUARANTY"),
        p("6.1 Unlimited personal guaranty from each owner of twenty percent or more of the Borrower."),
        section("7. CONDITIONS PRECEDENT"),
        p("Satisfied at closing; evidence retained in the Bank's loan file."),
        PageBreak(),
    ]
    for title, paragraphs in sections:
        story.append(section(title))
        story.extend(p(text) for text in paragraphs)
    story += [
        section("10. EVENTS OF DEFAULT"),
        p("Non-payment, breach of a covenant in Section 8 or 9 not cured within thirty days, misrepresentation, "
          "cross-default to other indebtedness of the Borrower or a Guarantor to the Bank, and insolvency."),
        section("11. FEES AND EXPENSES"),
        p("Origination fee of 0.50% of the Loan amount, paid at closing."),
        section("12. GOVERNING LAW"),
        p("The Commonwealth of Massachusetts."),
        section("SCHEDULE A - COLLATERAL"),
        p(collateral),
        p("Furniture, trade fixtures, office equipment, and inventory are excluded from the Collateral and from "
          "the collateral value used for the purposes of Section 8.1."),
        section("SCHEDULE 1 - NEGOTIATED COVENANTS"),
        p(
            "The following departures from the Bank's standard form were agreed by Credit Risk and applied to "
            "the executed text above.",
            "Small",
        ),
        table(
            [
                ["Section", "Standard form", "As executed"],
                ["8.1 Loan-to-Value", "Not to exceed 75% of appraised value", "Not to exceed 70% of appraised value"],
                ["8.2 Debt Service Coverage", "Not less than 1.25x", "Not less than 1.30x"],
                ["9.3 Financial Reporting", "Quarterly compliance certificate; tested quarterly", "Quarterly compliance certificate; tested quarterly on trailing twelve months (confirmed)"],
                ["Schedule A", "Personal property excluded from collateral value", "Personal property excluded (confirmed)"],
            ],
            widths=[1.5 * inch, 2.5 * inch, 2.5 * inch],
        ),
        section("COVENANT COMPLIANCE AT CLOSING"),
        table(
            [
                ["Measure", "Covenant", "At closing"],
                ["Loan-to-Value", "70%", "70%"],
                ["Debt Service Coverage Ratio", "1.30x", dscr_actual],
            ],
            widths=[2.5 * inch, 2.0 * inch, 2.0 * inch],
        ),
        section("SIGNATURES"),
        p(f"Executed by the parties on {signed_on}.", "Small"),
        table(
            [
                ["ACME BANK", borrower.upper()],
                ["By: /s/ Priya Shah", "By: /s/ Dana Whitfield"],
                ["Name: Priya Shah", "Name: Dana Whitfield"],
                ["Title: Chief Credit Officer", "Title: Chief Financial Officer"],
                [f"Date: {signed_on}", f"Date: {signed_on}"],
            ],
            widths=[3.45 * inch, 3.45 * inch],
        ),
        Spacer(1, 0.2 * inch),
        synthetic_note("executed loan agreement"),
    ]
    make_doc(path).build(story)
    return path


# --------------------------------------------------------------------------------------
# Pinecrest Dental Group (second borrower, early-stage application)
# --------------------------------------------------------------------------------------


def build_pinecrest_application():
    path = PDF_OUT / "pinecrest-loan-application-2026.pdf"
    story = doc_header(
        "SBA 7(a) Loan Application - Summary",
        f"Pinecrest Dental Group | Practice Expansion | Received by {BANK} | LN-2026-0088",
    )
    story += [
        section("1. Applicant"),
        table(
            [
                ["Field", "Value"],
                ["Borrowing entity", "Pinecrest Dental Group, P.C."],
                ["Industry", "Healthcare - dental practice"],
                ["Principal place of business", "410 Magnolia Avenue, Charlotte, North Carolina 28204"],
                ["Primary contact", "Sarah Kim, Practice Administrator, sarah.kim@pinecrestdental.example"],
                ["Years in operation", "9"],
                ["Existing relationship", "Operating accounts only"],
            ],
            widths=[2.1 * inch, 4.8 * inch],
        ),
        section("2. Request"),
        table(
            [
                ["Term requested", "Borrower position"],
                ["Loan amount", "$650,000"],
                ["Loan program", "SBA 7(a) term loan"],
                ["Purpose", "Fit-out of a second operatory suite and purchase of imaging equipment"],
                ["Requested term", "120 months"],
                ["Requested interest rate", "8.10% variable (Prime plus 2.25%)"],
                ["Collateral offered", "Business assets and the equipment purchased; no real estate"],
                ["Equity contribution", "$115,000"],
            ],
            widths=[2.1 * inch, 4.8 * inch],
        ),
        section("3. Ownership and Guarantors"),
        table(
            [
                ["Owner", "Ownership", "Guaranty offered"],
                ["Dr. Amara Fields, DDS", "60%", "Personal guaranty"],
                ["Dr. Luis Herrera, DDS", "40%", "Personal guaranty"],
            ],
            widths=[2.6 * inch, 1.4 * inch, 2.9 * inch],
        ),
        section("4. Status"),
        p("Application received. Financial statements attached; tax returns and SBA forms outstanding. "
          "Preliminary risk rating: Medium, pending underwriting."),
        Spacer(1, 0.2 * inch),
        synthetic_note("loan application"),
    ]
    make_doc(path).build(story)
    return path


def build_pinecrest_financials():
    path = PDF_OUT / "pinecrest-financial-statements-fy2025.pdf"
    story = doc_header(
        "Financial Statements - Fiscal Year 2025",
        "Pinecrest Dental Group, P.C. | Compiled | Year ended December 31, 2025",
    )
    story += [
        section("Income Statement"),
        table(
            [
                ["Line", "FY2025", "FY2024"],
                ["Patient service revenue, net", "$3,120,000", "$2,860,000"],
                ["Clinical supplies and lab fees", "$(468,000)", "$(431,000)"],
                ["Staff compensation", "$(1,248,000)", "$(1,144,000)"],
                ["Occupancy and administrative", "$(561,000)", "$(520,000)"],
                ["Depreciation", "$(96,000)", "$(88,000)"],
                ["Operating income", "$747,000", "$677,000"],
                ["Owner compensation", "$(520,000)", "$(480,000)"],
                ["Net income before tax", "$227,000", "$197,000"],
            ],
            widths=[3.3 * inch, 1.8 * inch, 1.8 * inch],
        ),
        section("Balance Sheet (December 31, 2025)"),
        table(
            [
                ["Assets", "Amount", "Liabilities and Equity", "Amount"],
                ["Cash", "$186,000", "Accounts payable", "$94,000"],
                ["Patient receivables, net", "$214,000", "Equipment leases", "$168,000"],
                ["Equipment, net", "$412,000", "Other liabilities", "$41,000"],
                ["Other assets", "$58,000", "Shareholders' equity", "$567,000"],
                ["Total assets", "$870,000", "Total liabilities and equity", "$870,000"],
            ],
            widths=[2.2 * inch, 1.2 * inch, 2.3 * inch, 1.2 * inch],
        ),
        section("Debt Service Coverage - Proposed Loan"),
        table(
            [
                ["Measure", "FY2025"],
                ["Cash available for debt service (after owner compensation, plus depreciation)", "$323,000"],
                ["Proposed annual debt service ($650,000 at 8.10%, 10-year term)", "$95,300"],
                ["Existing equipment lease payments", "$61,200"],
                ["Debt Service Coverage Ratio (combined)", "2.06x"],
            ],
            widths=[4.9 * inch, 2.0 * inch],
        ),
        Spacer(1, 0.2 * inch),
        synthetic_note("financial statement"),
    ]
    make_doc(path).build(story)
    return path


# --------------------------------------------------------------------------------------
# Structured fixtures
# --------------------------------------------------------------------------------------


def write_json():
    records = {
        "loan": {
            "loanId": "LN-2026-0042",
            "name": "Harborview Logistics Distribution Facility Loan 2026",
            "borrower": "Harborview Logistics",
            "borrowerEntity": BORROWER_2026,
            "applicantName": "Dana Whitfield",
            "applicantEmail": "dana.whitfield@harborviewlogistics.example",
            "loanType": "Commercial Real Estate",
            "status": "Underwriting",
            "loanAmount": 4800000,
            "termMonths": 120,
            "amortizationMonths": 300,
            "interestRate": 6.85,
            "collateralType": "Real Estate",
            "collateralValue": 5650000,
            "borrowerStatedCollateralValue": 6000000,
            "ltv": 85,
            "dscr": 1.12,
            "region": "Northeast",
            "loanOfficerName": "Alex Bennett",
            "underwriter": "Credit Risk",
            "riskRating": "High",
            "targetClosingDate": "2026-11-30",
            "maturityDate": None,
            "covenantReviewDate": "2027-03-31",
            "boxWorkspace": "LOS-2026-Harborview",
        },
        "salesforceOpportunity": {
            "id": "006-demo-harborview",
            "accountName": "Harborview Logistics",
            "name": "Harborview Logistics - Distribution Facility Acquisition",
            "stage": "Proposal/Price Quote",
            "amount": 4800000,
            "closeDate": "2026-11-30",
            "loanOfficer": "Alex Bennett",
            "products": ["Commercial Real Estate Term Loan"],
        },
        "priorLoans": [
            {
                "loanId": "LN-2023-0311",
                "name": "Harborview Logistics Revolving Line of Credit 2023",
                "loanType": "Line of Credit",
                "status": "Closed",
                "loanAmount": 1500000,
                "termMonths": 36,
                "interestRate": 7.25,
                "collateralType": "Receivables",
                "collateralValue": 2150000,
                "ltv": 70,
                "dscr": 1.34,
                "maturityDate": "2026-09-30",
                "negotiatedCovenants": {"ltvMax": 70, "dscrMin": 1.30, "testFrequency": "quarterly"},
            },
            {
                "loanId": "LN-2025-0148",
                "name": "Harborview Logistics Equipment Term Loan 2025",
                "loanType": "Equipment Finance",
                "status": "Closed",
                "loanAmount": 2150000,
                "termMonths": 60,
                "interestRate": 6.95,
                "collateralType": "Equipment",
                "collateralValue": 3075000,
                "ltv": 70,
                "dscr": 1.31,
                "maturityDate": "2030-05-31",
                "negotiatedCovenants": {"ltvMax": 70, "dscrMin": 1.30, "testFrequency": "quarterly"},
            },
        ],
        "creditApprovalMatrix": [
            {"condition": "loanAmount > 2500000", "approver": "Credit Committee", "slaHours": 72},
            {"condition": "ltv > 75", "approver": "Chief Credit Officer", "slaHours": 48},
            {"condition": "dscr < 1.25", "approver": "Chief Credit Officer", "slaHours": 48},
            {"condition": "collateralType = Real Estate", "approver": "Collateral Review", "slaHours": 48},
            {"condition": "interestRate < floor", "approver": "Pricing Committee", "slaHours": 24},
            {"condition": "riskRating in High,Critical", "approver": "Chief Credit Officer", "slaHours": 48},
        ],
    }
    (JSON_OUT / "harborview-los-records.json").write_text(
        json.dumps(records, indent=2) + "\n", encoding="utf-8", newline="\n"
    )

    playbook = {
        "loanToValue": {
            "standardPolicyId": "LOS-LTV-001",
            "standard": "Maximum 75% loan-to-value on owner-occupied commercial real estate, measured against a bank-ordered appraisal; furniture, fixtures and equipment excluded.",
            "exceptionPolicyId": "LOS-LTV-002",
            "exception": "Up to 80% with a 12-month interest reserve and an additional guaranty; Chief Credit Officer approval.",
            "escalateWhen": "Loan-to-value exceeds 80%, the collateral value relies on personal property or a borrower-supplied valuation, or the collateral definition is widened outside the covenant section.",
        },
        "debtServiceCoverage": {
            "standardPolicyId": "LOS-DSCR-001",
            "standard": "Minimum 1.25x on trailing-twelve-month net operating income, tested quarterly.",
            "exceptionPolicyId": "LOS-DSCR-002",
            "exception": "Minimum 1.15x with a cash reserve of six months' debt service, tested quarterly; Chief Credit Officer approval.",
            "escalateWhen": "Coverage falls below 1.15x, the test frequency is reduced, or the threshold is restated anywhere other than the financial covenant section.",
        },
        "pricing": {
            "standardPolicyId": "LOS-RATE-001",
            "standard": "Floor of SOFR plus 2.75%, never below 6.50%.",
            "exceptionPolicyId": "LOS-RATE-002",
            "exception": "Relationship pricing down to 6.00% with $500,000 or more in operating deposits; Pricing Committee approval.",
            "escalateWhen": "A rate below the floor is requested without qualifying deposits.",
        },
        "guaranty": {
            "standardPolicyId": "LOS-GUAR-001",
            "standard": "Unlimited personal guaranty from every owner of 20% or more.",
            "exceptionPolicyId": "LOS-GUAR-002",
            "exception": "Limited guaranty with 25% cash collateral; Loan Documentation approval.",
            "escalateWhen": "A limited or absent guaranty is proposed without cash collateral, or any 20%-plus owner is omitted.",
        },
    }
    (JSON_OUT / "credit-policy-playbook.json").write_text(
        json.dumps(playbook, indent=2) + "\n", encoding="utf-8", newline="\n"
    )


def main():
    build_loan_application()
    build_term_sheet_markup()
    build_financial_statements()
    build_tax_return_summary()
    build_bank_statements()
    build_appraisal()
    build_insurance()
    build_executed_loan_agreement(
        year=2023,
        loan_id="LN-2023-0311",
        facility="A revolving line of credit",
        facility_title="Revolving Line of Credit Agreement",
        amount="$1,500,000",
        term_months=36,
        rate="Variable at SOFR plus 2.75%, 7.25% per annum at closing, with a floor of 6.50%",
        collateral=(
            "A first-priority security interest in all present and future accounts receivable of the Borrower, "
            "the proceeds thereof, and the deposit accounts into which they are collected. Advances are limited "
            "to a borrowing base of eligible receivables; the collateral value for the purposes of Section 8.1 was "
            "established at $2,150,000 by a field examination ordered by the Bank."
        ),
        collateral_value="$2,150,000",
        dscr_actual="1.34x",
        maturity="September 30, 2026",
        signed_on="September 15, 2023",
        borrower="Harborview Logistics",
    )
    build_executed_loan_agreement(
        year=2025,
        loan_id="LN-2025-0148",
        facility="An equipment term loan",
        facility_title="Equipment Term Loan Agreement",
        amount="$2,150,000",
        term_months=60,
        rate="Fixed at 6.95% per annum for the term of the Loan",
        collateral=(
            "A first-priority security interest in the tractors, trailers, forklifts, and warehouse conveyor "
            "systems listed in the equipment schedule delivered at closing, together with all accessions and "
            "proceeds. The collateral value for the purposes of Section 8.1 was established at $3,075,000 by an "
            "equipment appraisal ordered by the Bank."
        ),
        collateral_value="$3,075,000",
        dscr_actual="1.31x",
        maturity="May 31, 2030",
        signed_on="May 20, 2025",
        borrower="Harborview Logistics",
        prior_year=2023,
    )
    build_environmental_report()
    build_pinecrest_application()
    build_pinecrest_financials()
    write_json()
    print(f"Wrote PDFs to {PDF_OUT}")
    print(f"Wrote JSON to {JSON_OUT}")


if __name__ == "__main__":
    main()
