import streamlit as st
import pandas as pd
import io
import os
import pypdf
from datetime import datetime, timedelta
import zoneinfo
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# ---------------------------------------------------------
# 1. PAGE & BRANDED DARK THEME CONFIGURATION
# ---------------------------------------------------------
st.set_page_config(
    page_title="Yenepoya Admission & Fee Engine",
    page_icon="🤖",
    layout="wide"
)

# Force KSA Standard Time (Asia/Riyadh UTC+3)
try:
    ksa_tz = zoneinfo.ZoneInfo("Asia/Riyadh")
    current_ksa_date = datetime.now(ksa_tz).date()
except Exception:
    current_ksa_date = datetime.now().date()

# Dark Tech Theme Styling
st.markdown("""
    <style>
    .stApp {
        background-color: #0F172A !important;
        color: #F8FAFC !important;
    }
    section[data-testid="stSidebar"] {
        background-color: #1E293B !important;
        border-right: 1px solid #334155;
    }
    section[data-testid="stSidebar"] * {
        color: #F8FAFC !important;
    }
    .main-header {
        background: linear-gradient(135deg, #1E293B 0%, #0F172A 100%);
        border: 1px solid #38BDF8;
        color: #FFFFFF;
        padding: 24px;
        border-radius: 12px;
        margin-bottom: 25px;
        box-shadow: 0 4px 15px rgba(56, 189, 248, 0.15);
    }
    .main-header h1 {
        color: #38BDF8 !important;
        margin: 0;
        font-weight: 700;
        letter-spacing: 0.5px;
    }
    .main-header p {
        color: #F59E0B !important;
        margin-top: 5px;
        font-size: 1.05rem;
        font-weight: 600;
    }
    .quote-box {
        background-color: #1E293B;
        border: 1px solid #334155;
        border-left: 5px solid #F59E0B;
        border-radius: 8px;
        padding: 20px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        margin-bottom: 20px;
    }
    [data-testid="stMetricValue"] {
        color: #38BDF8 !important;
    }
    </style>
""", unsafe_allow_html=True)

# Header Section
logo_path = "our-logo.png"

col_header_left, col_header_right = st.columns([1, 4])
with col_header_left:
    if os.path.exists(logo_path):
        st.image(logo_path, width=110)
    else:
        st.write("🤖")

with col_header_right:
    st.markdown("""
        <div class="main-header">
            <h1>YENEPOYA INTERNATIONAL SCHOOL</h1>
            <p>A Next Generation of Learning — Official Parent Fee Quotation Portal</p>
        </div>
    """, unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. MASTER DATA MAPPINGS
# ---------------------------------------------------------
books_fee_map = {
    "KG. 1": 500, "KG. 2": 500, "KG. 3": 500,
    "Grade 1": 1200, "Grade 2": 1200, "Grade 3": 1200,
    "Grade 4": 1500, "Grade 5": 1500, "Grade 6": 1500,
    "Grade 7": 1500, "Grade 8": 1500, "Grade 9": 1500,
    "Grade 10": 1800, "Grade 11": 1800, "Grade 12": 2000
}

new_tuition_map = {
    "KG. 1": 26000, "KG. 2": 26000, "KG. 3": 28000,
    "Grade 1": 33000, "Grade 2": 33000, "Grade 3": 33000,
    "Grade 4": 33000, "Grade 5": 36000, "Grade 6": 36000,
    "Grade 7": 36000, "Grade 8": 36000, "Grade 9": 36000,
    "Grade 10": 38000, "Grade 11": 40000, "Grade 12": 42000
}

old_tuition_map = {
    "KG. 1": 21500, "KG. 2": 21500, "KG. 3": 23500,
    "Grade 1": 28500, "Grade 2": 28500, "Grade 3": 28500,
    "Grade 4": 30500, "Grade 5": 30500, "Grade 6": 30500,
    "Grade 7": 31500, "Grade 8": 32500, "Grade 9": 32500,
    "Grade 10": 34500, "Grade 11": 36500, "Grade 12": 38500
}

# ---------------------------------------------------------
# 3. SIDEBAR CONTROLS & VALIDITY SETTINGS
# ---------------------------------------------------------
st.sidebar.header("⚙️ Student & Family Setup")
num_students = st.sidebar.number_input("Number of Students", min_value=1, max_value=6, value=1, step=1)
nationality = st.sidebar.selectbox("Nationality (Tax Category)", ["Saudi National (0% VAT)", "Non-Saudi (15% VAT)"])
parent_name = st.sidebar.text_input("Parent / Guardian Name", "Parent/Guardian")

is_non_saudi = "Non-Saudi" in nationality
vat_rate = 0.15 if is_non_saudi else 0.0

st.sidebar.divider()
st.sidebar.header("📅 Date & Validity Controls")
issue_date = st.sidebar.date_input("Quotation Issue Date (KSA)", value=current_ksa_date)
discount_validity_days = st.sidebar.slider("Discount Validity (Days)", min_value=1, max_value=60, value=15)
quote_validity_days = st.sidebar.slider("Quotation Validity (Days)", min_value=1, max_value=90, value=30)

discount_expiry_date = issue_date + timedelta(days=discount_validity_days)
quote_expiry_date = issue_date + timedelta(days=quote_validity_days)

family_total_quote = 0.0
family_first_payment = 0.0
family_second_payment = 0.0
student_summaries = []
full_ipad_pkg_students = []

# ---------------------------------------------------------
# 4. DYNAMIC STUDENT INPUT TABS
# ---------------------------------------------------------
tabs = st.tabs([f"🎓 Student {i+1}" for i in range(num_students)])

for i, tab in enumerate(tabs):
    with tab:
        st.subheader(f"Student {i+1} Configuration")
        
        student_name_input = st.text_input(f"Student {i+1} Full Name", value=f"Student {i+1}", key=f"name_{i}")
        
        c1, c2, c3 = st.columns(3)
        
        with c1:
            student_type = st.selectbox("Student Status", ["New Student", "Returning Student"], key=f"status_{i}")
            grade = st.selectbox("Select Grade", list(new_tuition_map.keys()), key=f"grade_{i}")
            
        with c2:
            default_discount = 35 + (5 if i > 0 else 0)
            discount_pct = st.slider("Discount (%)", 0, 50, min(default_discount, 50), 5, key=f"disc_{i}")
            
            ipad_option = st.selectbox(
                "iPad Package / Migration",
                [
                    "None",
                    "SAR 2,800 - Full iPad Package (Spot Payment Offer)",
                    "SAR 600 - Migration Only (License & Config)",
                    "SAR 700 - Migration with Pen",
                    "SAR 800 - Migration with Pen & Cover"
                ],
                key=f"ipad_opt_{i}"
            )
            
        with c3:
            bus_options_list = [
                "None",
                "One Side (1 Term) - SAR 1,500",
                "One Side (Whole Year) - SAR 3,000",
                "Two Side (Whole Year) - SAR 5,000",
                "Two Side Premium (Whole Year) - SAR 6,500"
            ]
            if student_type == "Returning Student":
                bus_options_list.extend([
                    "Old Student: 1 Side Whole Year - SAR 2,000",
                    "Old Student: 2 Side Whole Year - SAR 4,000"
                ])
                
            bus_option = st.selectbox("Bus Transportation", bus_options_list, key=f"bus_{i}")

        if student_type == "Returning Student":
            base_tuition = old_tuition_map.get(grade, 28500)
        else:
            base_tuition = new_tuition_map.get(grade, 33000)

        discount_amount = base_tuition * (discount_pct / 100.0)
        net_tuition = base_tuition - discount_amount
        
        vat_amount = net_tuition * vat_rate
        tuition_with_vat = net_tuition + vat_amount

        books_fee = books_fee_map.get(grade, 1200)
        
        ipad_fee = 0
        if "2,800" in ipad_option:
            ipad_fee = 2800
            full_ipad_pkg_students.append(student_name_input)
        elif "600" in ipad_option:
            ipad_fee = 600
        elif "700" in ipad_option:
            ipad_fee = 700
        elif "800" in ipad_option:
            ipad_fee = 800

        bus_fee = 0
        if "1,500" in bus_option:
            bus_fee = 1500
        elif "2,000" in bus_option:
            bus_fee = 2000
        elif "3,000" in bus_option:
            bus_fee = 3000
        elif "4,000" in bus_option:
            bus_fee = 4000
        elif "5,000" in bus_option:
            bus_fee = 5000
        elif "6,500" in bus_option:
            bus_fee = 6500

        total_student_fee = tuition_with_vat + books_fee + ipad_fee + bus_fee
        first_pay = (tuition_with_vat / 2) + books_fee
        second_pay = (tuition_with_vat / 2) + ipad_fee + bus_fee

        family_total_quote += total_student_fee
        family_first_payment += first_pay
        family_second_payment += second_pay

        student_summaries.append({
            "Student Name": student_name_input,
            "Student Status": student_type,
            "Grade": grade,
            "Base Tuition": base_tuition,
            "Discount %": f"{discount_pct}%",
            "Discount Amt": discount_amount,
            "VAT": vat_amount,
            "Mandatory Books": books_fee,
            "iPad Fee": ipad_fee,
            "Bus Fee": bus_fee,
            "Total Fee (SAR)": total_student_fee
        })

        st.markdown('<div class="quote-box">', unsafe_allow_html=True)
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Base Tuition", f"{base_tuition:,.2f} SAR")
        m2.metric(f"Discount ({discount_pct}%)", f"-{discount_amount:,.2f} SAR")
        m3.metric("Mandatory Books", f"{books_fee:,.2f} SAR")
        m4.metric("iPad & Bus Add-Ons", f"{ipad_fee + bus_fee:,.2f} SAR")
        m5.metric("Student Total", f"{total_student_fee:,.2f} SAR")
        st.markdown('</div>', unsafe_allow_html=True)

# ---------------------------------------------------------
# 5. STREAMLIT SCREEN SUMMARY DISPLAY
# ---------------------------------------------------------
st.divider()
st.subheader("📊 Official Family Quotation Breakdown")

val_col1, val_col2, val_col3 = st.columns(3)
val_col1.info(f"📅 **Issue Date (KSA):** {issue_date.strftime('%d %b %Y')}")
val_col2.warning(f"⏳ **Discount Valid Until:** {discount_expiry_date.strftime('%d %b %Y')} ({discount_validity_days} Days)")
val_col3.error(f"🛑 **Quotation Expires:** {quote_expiry_date.strftime('%d %b %Y')} ({quote_validity_days} Days)")

metrics_labels = [
    "Student Status",
    "Grade Level",
    "Base Tuition (SAR)",
    "Discount Percentage",
    "Discount Amount (SAR)",
    "VAT Amount (SAR)" if is_non_saudi else "VAT Amount (SAR)",
    "Mandatory Books Fee (SAR)",
    "iPad Package / Migration (SAR)",
    "Bus Transportation (SAR)",
    "Student Total Fee (SAR)"
]

horizontal_data = {"Fee Component": metrics_labels}

for s in student_summaries:
    col_name = s["Student Name"]
    horizontal_data[col_name] = [
        s["Student Status"],
        s["Grade"],
        f"{s['Base Tuition']:,.2f}",
        s["Discount %"],
        f"-{s['Discount Amt']:,.2f}",
        f"+{s['VAT']:,.2f}",
        f"{s['Mandatory Books']:,.2f}",
        f"{s['iPad Fee']:,.2f}",
        f"{s['Bus Fee']:,.2f}",
        f"{s['Total Fee (SAR)']:,.2f}"
    ]

df_horizontal = pd.DataFrame(horizontal_data)
st.table(df_horizontal)

st.subheader("📋 Student Totals Summary Table")

totals_table_data = []
for idx, s in enumerate(student_summaries):
    row = {
        "Student": f"Student {idx+1}: {s['Student Name']}",
        "Grade": s["Grade"],
        "Net School Tuition": f"{s['Base Tuition'] - s['Discount Amt']:,.2f} SAR",
    }
    if is_non_saudi:
        row["VAT (15% on Tuition)"] = f"{s['VAT']:,.2f} SAR"
    row["Books & Add-Ons"] = f"{s['Mandatory Books'] + s['iPad Fee'] + s['Bus Fee']:,.2f} SAR"
    row["Total Amount"] = f"{s['Total Fee (SAR)']:,.2f} SAR"
    totals_table_data.append(row)

st.table(pd.DataFrame(totals_table_data))

st.markdown(f"### **Grand Total Quote: `{family_total_quote:,.2f} SAR`**")

col_p1, col_p2 = st.columns(2)
col_p1.info(f"**Term 1 Payment Required:** `{family_first_payment:,.2f} SAR`")
col_p2.success(f"**Term 2 Payment Required:** `{family_second_payment:,.2f} SAR`")

if len(full_ipad_pkg_students) > 0:
    with st.container(border=True):
        st.subheader("📱 Full Student iPad Package Details")
        st.markdown(f"**Selected for Student(s):** :blue[{', '.join(full_ipad_pkg_students)}]")
        st.divider()

        col_hw, col_sw = st.columns(2)
        with col_hw:
            st.markdown("**📦 Included Hardware & Protection:**")
            st.markdown("""
            * **Brand New iPad A16 (128GB Storage)**
            * **Rugged Heavy-Duty Protective Case**
            * **School-Approved High-Precision Stylus Pen**
            * **AppleCare+ Enterprise Warranty** (36 Months full coverage)
            """)

        with col_sw:
            st.markdown("**⚙️ Digital Ecosystem & Management:**")
            st.markdown("""
            * **Jamf School Management System** (MDM)
            * **Microsoft 365 Education Account** (1TB Cloud storage)
            * **Apple Managed Educational ID & 200GB iCloud**
            * **Pre-configured Security Profiles & Learning Apps**
            """)

        st.divider()

        st.warning(
            "**💳 Payment Terms Policy:**\n\n"
            "The discounted rate of **SAR 2,800** is an **instant/spot payment offer** at the time of registration. "
            "If choosing the **C-Pay 12-Month Installment Plan**, the total price is **SAR 3,000** (12 monthly payments of SAR 250)."
        )

        st.error(
            "**⚠️ Annual Software License Renewal Notice:**\n\n"
            "The initial package fee covers Year 1 hardware, provisioning, and software setups. "
            "All active management licenses (Jamf MDM, Microsoft 365, Cloud platform access) **must be renewed annually** "
            "by parents to keep the device compliant with school systems."
        )

st.divider()

# ---------------------------------------------------------
# 6. EXACT MATCH PDF GENERATOR
# ---------------------------------------------------------
def create_pdf_bytes():
    try:
        content_buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            content_buffer, 
            pagesize=letter, 
            rightMargin=25, 
            leftMargin=25, 
            topMargin=115, 
            bottomMargin=60
        )
        
        elements = []
        styles = getSampleStyleSheet()

        section_heading_style = ParagraphStyle(
            'SectionHeader',
            parent=styles['Heading2'],
            fontName='Helvetica-Bold',
            fontSize=11,
            leading=14,
            textColor=colors.HexColor('#0B2545'),
            spaceBefore=6,
            spaceAfter=6
        )
        
        meta_style = ParagraphStyle(
            'MetaText',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=8,
            leading=11,
            textColor=colors.HexColor('#333333')
        )

        cell_hdr_style = ParagraphStyle(
            'TableHdr',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=7.5,
            leading=9,
            textColor=colors.white,
            alignment=1
        )
        
        cell_body_style = ParagraphStyle(
            'TableBody',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=7.5,
            leading=9,
            textColor=colors.HexColor('#1E293B'),
            alignment=1
        )

        cell_body_left = ParagraphStyle(
            'TableBodyLeft',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=7.5,
            leading=9,
            textColor=colors.HexColor('#0B2545'),
            alignment=0
        )

        # Meta Header Box
        elements.append(Paragraph(f"<b>Parent / Guardian:</b> {parent_name} &nbsp;&nbsp;|&nbsp;&nbsp; <b>Tax Status:</b> {nationality}", meta_style))
        elements.append(Paragraph(f"<b>Issue Date:</b> {issue_date.strftime('%d %b %Y')} &nbsp;&nbsp;|&nbsp;&nbsp; <b>Discount Valid Until:</b> {discount_expiry_date.strftime('%d %b %Y')} ({discount_validity_days} Days) &nbsp;&nbsp;|&nbsp;&nbsp; <b>Quote Expires:</b> {quote_expiry_date.strftime('%d %b %Y')} ({quote_validity_days} Days)", meta_style))
        elements.append(Spacer(1, 8))

        # -----------------------------------------------------
        # TABLE 1: OFFICIAL FAMILY QUOTATION BREAKDOWN
        # -----------------------------------------------------
        elements.append(Paragraph("📊 Official Family Quotation Breakdown", section_heading_style))
        
        t1_headers = [Paragraph("Fee Component", cell_body_left)] + [Paragraph(s["Student Name"], cell_hdr_style) for s in student_summaries]
        t1_data = [t1_headers]

        for idx, row_name in enumerate(metrics_labels):
            row_cells = [Paragraph(row_name, cell_body_left)]
            for s in student_summaries:
                if idx == 0: val = s["Student Status"]
                elif idx == 1: val = s["Grade"]
                elif idx == 2: val = f"{s['Base Tuition']:,.2f}"
                elif idx == 3: val = s["Discount %"]
                elif idx == 4: val = f"-{s['Discount Amt']:,.2f}"
                elif idx == 5: val = f"+{s['VAT']:,.2f}"
                elif idx == 6: val = f"{s['Mandatory Books']:,.2f}"
                elif idx == 7: val = f"{s['iPad Fee']:,.2f}"
                elif idx == 8: val = f"{s['Bus Fee']:,.2f}"
                elif idx == 9: val = f"<b>{s['Total Fee (SAR)']:,.2f}</b>"
                row_cells.append(Paragraph(str(val), cell_body_style))
            t1_data.append(row_cells)

        num_cols = len(t1_headers)
        f_width = 160
        r_width = (562 - f_width) / max(1, num_cols - 1)
        t1_col_widths = [f_width] + [r_width] * (num_cols - 1)

        pdf_t1 = Table(t1_data, colWidths=t1_col_widths)
        pdf_t1.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0B2545')),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
            ('TOPPADDING', (0,0), (-1,-1), 3),
            ('BOTTOMPADDING', (0,0), (-1,-1), 3),
            ('BACKGROUND', (0,1), (-1,-1), colors.HexColor('#F8FAFC')),
        ]))
        elements.append(pdf_t1)
        elements.append(Spacer(1, 10))

        # -----------------------------------------------------
        # TABLE 2: STUDENT TOTALS SUMMARY TABLE
        # -----------------------------------------------------
        elements.append(Paragraph("📋 Student Totals Summary Table", section_heading_style))
        
        if is_non_saudi:
            t2_headers = ["Student", "Grade", "Net School Tuition", "VAT (15%)", "Books & Add-Ons", "Total Amount"]
            t2_widths = [120, 50, 100, 85, 100, 107]
        else:
            t2_headers = ["Student", "Grade", "Net School Tuition", "Books & Add-Ons", "Total Amount"]
            t2_widths = [140, 60, 120, 120, 122]

        t2_data = [[Paragraph(h, cell_hdr_style) for h in t2_headers]]

        for idx, s in enumerate(student_summaries):
            net_t = s['Base Tuition'] - s['Discount Amt']
            add_ons = s['Mandatory Books'] + s['iPad Fee'] + s['Bus Fee']
            
            if is_non_saudi:
                row = [
                    Paragraph(f"Student {idx+1}: {s['Student Name']}", cell_body_left),
                    Paragraph(s['Grade'], cell_body_style),
                    Paragraph(f"{net_t:,.2f} SAR", cell_body_style),
                    Paragraph(f"{s['VAT']:,.2f} SAR", cell_body_style),
                    Paragraph(f"{add_ons:,.2f} SAR", cell_body_style),
                    Paragraph(f"<b>{s['Total Fee (SAR)']:,.2f} SAR</b>", cell_body_style)
                ]
            else:
                row = [
                    Paragraph(f"Student {idx+1}: {s['Student Name']}", cell_body_left),
                    Paragraph(s['Grade'], cell_body_style),
                    Paragraph(f"{net_t:,.2f} SAR", cell_body_style),
                    Paragraph(f"{add_ons:,.2f} SAR", cell_body_style),
                    Paragraph(f"<b>{s['Total Fee (SAR)']:,.2f} SAR</b>", cell_body_style)
                ]
            t2_data.append(row)

        pdf_t2 = Table(t2_data, colWidths=t2_widths)
        pdf_t2.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1E293B')),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
            ('TOPPADDING', (0,0), (-1,-1), 4),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
            ('BACKGROUND', (0,1), (-1,-1), colors.HexColor('#FFFFFF')),
        ]))
        elements.append(pdf_t2)
        elements.append(Spacer(1, 8))

        # -----------------------------------------------------
        # GRAND TOTAL & TERM PAYMENT BANNER
        # -----------------------------------------------------
        summary_p_style = ParagraphStyle(
            'GrandTotalBanner',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=9.5,
            leading=13,
            textColor=colors.HexColor('#0B2545')
        )
        
        banner_text = f"<b>Grand Total Quote:</b> <font color='#059669'>{family_total_quote:,.2f} SAR</font> &nbsp;&nbsp;|&nbsp;&nbsp; <b>Term 1 Payment:</b> {family_first_payment:,.2f} SAR &nbsp;&nbsp;|&nbsp;&nbsp; <b>Term 2 Payment:</b> {family_second_payment:,.2f} SAR"
        elements.append(Paragraph(banner_text, summary_p_style))

        # -----------------------------------------------------
        # FULL STUDENT IPAD PACKAGE DETAILS BOX (IF APPLICABLE)
        # -----------------------------------------------------
        if len(full_ipad_pkg_students) > 0:
            elements.append(Spacer(1, 10))
            elements.append(Paragraph("📱 Full Student iPad Package Details", section_heading_style))
            elements.append(Paragraph(f"<b>Selected for Student(s):</b> {', '.join(full_ipad_pkg_students)}", meta_style))
            elements.append(Spacer(1, 4))

            ipad_hdr_style = ParagraphStyle('IpadHdr', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8, leading=10, textColor=colors.HexColor('#0B2545'))
            ipad_item_style = ParagraphStyle('IpadItem', parent=styles['Normal'], fontName='Helvetica', fontSize=7.5, leading=10, textColor=colors.HexColor('#334155'))

            col1_content = [
                Paragraph("<b>📦 Included Hardware & Protection:</b>", ipad_hdr_style),
                Paragraph("• Brand New iPad A16 (128GB Storage)", ipad_item_style),
                Paragraph("• Rugged Heavy-Duty Protective Case", ipad_item_style),
                Paragraph("• School-Approved High-Precision Stylus Pen", ipad_item_style),
                Paragraph("• AppleCare+ Enterprise Warranty (36 Months)", ipad_item_style),
            ]
            
            col2_content = [
                Paragraph("<b>⚙️ Digital Ecosystem & Management:</b>", ipad_hdr_style),
                Paragraph("• Jamf School Management System (MDM)", ipad_item_style),
                Paragraph("• Microsoft 365 Education Account (1TB Cloud)", ipad_item_style),
                Paragraph("• Apple Managed Educational ID & 200GB iCloud", ipad_item_style),
                Paragraph("• Pre-configured Security Profiles & Learning Apps", ipad_item_style),
            ]

            ipad_spec_table = Table([[col1_content, col2_content]], colWidths=[281, 281])
            ipad_spec_table.setStyle(TableStyle([
                ('VALIGN', (0,0), (-1,-1), 'TOP'),
                ('LEFTPADDING', (0,0), (-1,-1), 0),
                ('RIGHTPADDING', (0,0), (-1,-1), 0),
                ('TOPPADDING', (0,0), (-1,-1), 0),
                ('BOTTOMPADDING', (0,0), (-1,-1), 0),
            ]))
            elements.append(ipad_spec_table)
            elements.append(Spacer(1, 6))

            # Payment Terms Callout
            policy_style = ParagraphStyle('PolicyBox', parent=styles['Normal'], fontName='Helvetica', fontSize=7.5, leading=10, textColor=colors.HexColor('#1E293B'))
            
            p_terms = "<b>💳 Payment Terms Policy:</b> The discounted rate of <b>SAR 2,800</b> is an <b>instant/spot payment offer</b> at the time of registration. If choosing the <b>C-Pay 12-Month Installment Plan</b>, the total price is <b>SAR 3,000</b> (12 monthly payments of SAR 250)."
            p_table = Table([[Paragraph(p_terms, policy_style)]], colWidths=[562])
            p_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#FEF3C7')),
                ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#F59E0B')),
                ('TOPPADDING', (0,0), (-1,-1), 4),
                ('BOTTOMPADDING', (0,0), (-1,-1), 4),
                ('LEFTPADDING', (0,0), (-1,-1), 6),
                ('RIGHTPADDING', (0,0), (-1,-1), 6),
            ]))
            elements.append(p_table)
            elements.append(Spacer(1, 4))

            # License Renewal Callout
            p_renew = "<b>⚠️ Annual Software License Renewal Notice:</b> The initial package fee covers Year 1 hardware, provisioning, and software setups. All active management licenses (Jamf MDM, Microsoft 365, Cloud platform access) <b>must be renewed annually</b> by parents to keep the device compliant with school systems."
            r_table = Table([[Paragraph(p_renew, policy_style)]], colWidths=[562])
            r_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#FEE2E2')),
                ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#EF4444')),
                ('TOPPADDING', (0,0), (-1,-1), 4),
                ('BOTTOMPADDING', (0,0), (-1,-1), 4),
                ('LEFTPADDING', (0,0), (-1,-1), 6),
                ('RIGHTPADDING', (0,0), (-1,-1), 6),
            ]))
            elements.append(r_table)

        doc.build(elements)
        content_buffer.seek(0)

        template_path = "LetterHead (Updated).pdf"
        if os.path.exists(template_path):
            reader_template = pypdf.PdfReader(template_path)
            reader_content = pypdf.PdfReader(content_buffer)
            
            writer = pypdf.PdfWriter()
            template_page = reader_template.pages[0]
            content_page = reader_content.pages[0]
            
            template_page.merge_page(content_page)
            writer.add_page(template_page)
            
            final_buffer = io.BytesIO()
            writer.write(final_buffer)
            final_buffer.seek(0)
            return final_buffer.getvalue()
        else:
            return content_buffer.getvalue()
            
    except Exception as err:
        st.error(f"Error generating PDF: {err}")
        return b""

btn_col1, btn_col2 = st.columns(2)

with btn_col1:
    st.components.v1.html(
        """
        <button onclick="window.parent.print()" style="background-color: #38BDF8; color: #0F172A; padding: 12px 20px; border: none; border-radius: 6px; cursor: pointer; width: 100%; font-weight: bold; font-size: 14px;">
            🖨️ Print Quotation Directly
        </button>
        """,
        height=50
    )

with btn_col2:
    pdf_data = create_pdf_bytes()
    if pdf_data:
        st.download_button(
            label="📄 Export Official Letterhead PDF",
            data=pdf_data,
            file_name=f"Yenepoya_Fee_Quotation_{parent_name.replace(' ', '_')}.pdf",
            mime="application/pdf",
            use_container_width=True
        )
