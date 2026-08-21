import streamlit as st
import pandas as pd
import io
import os
import pypdf
from datetime import datetime, timedelta
import zoneinfo
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
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
    @media print {
        [data-testid="stSidebar"], .stButton, header, footer {
            display: none !important;
        }
        .main .block-container {
            padding: 0 !important;
        }
        body, .stApp {
            background-color: white !important;
            color: black !important;
        }
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
            <p>A Next Generation of Learning — Fee Quotation Portal</p>
        </div>
    """, unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. MASTER DATA MAPPINGS (GRADES KG1 - GRADE 12)
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

cert_fee_map = {"Grade 7": 300, "Grade 9": 400, "Grade 10": 500, "Grade 11": 500, "Grade 12": 600}

# ---------------------------------------------------------
# 3. SIDEBAR CONTROLS & VALIDITY SETTINGS
# ---------------------------------------------------------
st.sidebar.header("⚙️ Student & Family Setup")
num_students = st.sidebar.number_input("Number of Students", min_value=1, max_value=6, value=1, step=1)
nationality = st.sidebar.selectbox("Nationality (Tax Category)", ["Saudi National (0% VAT)", "Non-Saudi (15% VAT)"])
parent_name = st.sidebar.text_input("Parent / Guardian Name", "Parent/Guardian")

st.sidebar.divider()
st.sidebar.header("📅 Date & Validity Controls")

# Automatic KSA Issue Date
issue_date = st.sidebar.date_input("Quotation Issue Date (KSA)", value=current_ksa_date)

# Dynamic Validity Selectors
discount_validity_days = st.sidebar.slider("Discount Validity (Days)", min_value=1, max_value=60, value=15)
quote_validity_days = st.sidebar.slider("Quotation Validity (Days)", min_value=1, max_value=90, value=30)

discount_expiry_date = issue_date + timedelta(days=discount_validity_days)
quote_expiry_date = issue_date + timedelta(days=quote_validity_days)

vat_rate = 0.15 if "Non-Saudi" in nationality else 0.0

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
            
            # Expanded iPad Dropdown Menu
            ipad_option = st.selectbox(
                "iPad / Migration Option",
                [
                    "None",
                    "SAR 2,800 - Full Package (Spot Payment)",
                    "SAR 600 - Migration Only (License & Config)",
                    "SAR 700 - Migration with Pen",
                    "SAR 800 - Migration with Pen & Cover"
                ],
                key=f"ipad_opt_{i}"
            )
            
        with c3:
            # Dynamic Transportation Selector
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

        # Fee Calculations
        if student_type == "Returning Student":
            base_tuition = old_tuition_map.get(grade, 28500)
        else:
            base_tuition = new_tuition_map.get(grade, 33000)

        discount_amount = base_tuition * (discount_pct / 100.0)
        net_tuition = base_tuition - discount_amount
        vat_amount = net_tuition * vat_rate
        tuition_with_vat = net_tuition + vat_amount

        # Mandatory Book Fee
        books_fee = books_fee_map.get(grade, 1200)
        cert_fee = cert_fee_map.get(grade, 0)
        
        # iPad Fee Parse
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

        # Bus Fee Parse
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

        total_student_fee = tuition_with_vat + books_fee + cert_fee + ipad_fee + bus_fee
        first_pay = (tuition_with_vat / 2) + books_fee + cert_fee
        second_pay = (tuition_with_vat / 2) + ipad_fee + bus_fee

        family_total_quote += total_student_fee
        family_first_payment += first_pay
        family_second_payment += second_pay

        student_summaries.append({
            "Student Name": student_name_input,
            "Status": student_type,
            "Grade": grade,
            "Base Tuition": base_tuition,
            "Discount %": f"{discount_pct}%",
            "Discount Amt": discount_amount,
            "VAT": vat_amount,
            "Mandatory Books": books_fee,
            "Cert Fee": cert_fee,
            "iPad Fee": ipad_fee,
            "Bus Fee": bus_fee,
            "Total (SAR)": total_student_fee
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
# 5. CONSOLIDATED SUMMARY & VALIDITY DISPLAY
# ---------------------------------------------------------
st.divider()
st.subheader("📊 Official Family Quotation Summary")

# Display Validity Badges
val_col1, val_col2, val_col3 = st.columns(3)
val_col1.info(f"📅 **Issue Date (KSA):** {issue_date.strftime('%d %b %Y')}")
val_col2.warning(f"⏳ **Discount Valid Until:** {discount_expiry_date.strftime('%d %b %Y')} ({discount_validity_days} Days)")
val_col3.error(f"🛑 **Quotation Expires:** {quote_expiry_date.strftime('%d %b %Y')} ({quote_validity_days} Days)")

df_family = pd.DataFrame(student_summaries)
st.dataframe(df_family.style.format({
    "Base Tuition": "{:,.2f}",
    "Discount Amt": "-{:,.2f}",
    "VAT": "+{:,.2f}",
    "Mandatory Books": "{:,.2f}",
    "Cert Fee": "{:,.2f}",
    "iPad Fee": "{:,.2f}",
    "Bus Fee": "{:,.2f}",
    "Total (SAR)": "{:,.2f}"
}), use_container_width=True)

st.markdown(f"### **Grand Total Family Quote: `{family_total_quote:,.2f} SAR`**")

col_p1, col_p2 = st.columns(2)
col_p1.info(f"**Total First Installment:** `{family_first_payment:,.2f} SAR`")
col_p2.success(f"**Total Second Installment:** `{family_second_payment:,.2f} SAR`")

# Render iPad Specifications, Installment Notice & Renewal Warning
if len(full_ipad_pkg_students) > 0:
    st.divider()
    st.subheader("📱 Full Student iPad Package Specifications & Compliance")
    st.write(f"**Selected for:** {', '.join(full_ipad_pkg_students)}")
    
    st.markdown("""
    * **Hardware & Accessories:** New iPad A16 (128GB), Rugged Protective Cover, and School-Approved Stylus.
    * **Security & Coverage:** AppleCare+ for Enterprise (36 Months coverage).
    * **Software & Managed Accounts:** Jamf School Management (MDM), Microsoft School Account (1TB Cloud), 200GB iCloud & Apple Managed Account.
    * **Technical Services:** Full device configuration, security profiles, and school app suite setup.
    
    > 💳 **PAYMENT TERMS NOTICE:**  
    > *The **SAR 2,800** price is valid **ONLY for instant/spot payment** at registration. If paying via C-Pay 12-month installment, total price is **SAR 3,000** (12 monthly payments of SAR 250).*
    
    > ⚠️ **IMPORTANT ANNUAL RENEWAL NOTICE:**  
    > *The initial package fee covers Year 1 device provisioning and software licensing. All software management licenses (Jamf MDM, Microsoft 365, Cloud services) **must be renewed annually** by the parent/guardian to maintain device network access.*
    """)

st.divider()

# ---------------------------------------------------------
# 6. PDF GENERATION BUILDER WITH EXPANDED COLUMNS
# ---------------------------------------------------------
def create_pdf_bytes():
    try:
        content_buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            content_buffer, 
            pagesize=letter, 
            rightMargin=25, 
            leftMargin=25, 
            topMargin=125, 
            bottomMargin=75
        )
        
        elements = []
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            'DocTitle',
            parent=styles['Heading1'],
            fontName='Helvetica-Bold',
            fontSize=13,
            leading=16,
            textColor=colors.HexColor('#0B2545'),
            spaceAfter=8
        )
        
        meta_style = ParagraphStyle(
            'MetaText',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=8.5,
            leading=12,
            textColor=colors.HexColor('#333333')
        )

        elements.append(Paragraph("OFFICIAL ADMISSION FEE QUOTATION", title_style))
        elements.append(Paragraph(f"<b>Parent / Guardian:</b> {parent_name} &nbsp;&nbsp;|&nbsp;&nbsp; <b>Tax Status:</b> {nationality}", meta_style))
        elements.append(Paragraph(f"<b>Issue Date:</b> {issue_date.strftime('%d %b %Y')} &nbsp;&nbsp;|&nbsp;&nbsp; <b>Discount Valid Until:</b> {discount_expiry_date.strftime('%d %b %Y')} &nbsp;&nbsp;|&nbsp;&nbsp; <b>Quote Expiry:</b> {quote_expiry_date.strftime('%d %b %Y')}", meta_style))
        elements.append(Spacer(1, 10))

        # Explicit Multi-Column PDF Header Table
        table_data = [["Student Name", "Grade", "Base Tuition", "Disc %", "Disc Amt", "Books", "Cert", "iPad", "Bus", "Total (SAR)"]]
        for s in student_summaries:
            table_data.append([
                str(s["Student Name"]), 
                str(s["Grade"]), 
                f"{s['Base Tuition']:,.0f}", 
                str(s["Discount %"]),
                f"-{s['Discount Amt']:,.0f}", 
                f"{s['Mandatory Books']:,.0f}",
                f"{s['Cert Fee']:,.0f}",
                f"{s['iPad Fee']:,.0f}",
                f"{s['Bus Fee']:,.0f}",
                f"{s['Total (SAR)']:,.2f}"
            ])
        
        # Exact column width alignment (562pt total letter printable width)
        pdf_table = Table(table_data, colWidths=[90, 45, 60, 40, 55, 45, 35, 40, 40, 112])
        pdf_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0B2545')),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,-1), 8),
            ('BOTTOMPADDING', (0,0), (-1,-1), 5),
            ('TOPPADDING', (0,0), (-1,-1), 5),
        ]))
        elements.append(pdf_table)
        elements.append(Spacer(1, 10))
        
        summary_text = f"""
        <b>Grand Total Quote:</b> {family_total_quote:,.2f} SAR<br/>
        <font color='#475569'>First Installment: {family_first_payment:,.2f} SAR &nbsp;|&nbsp; Second Installment: {family_second_payment:,.2f} SAR</font>
        """
        elements.append(Paragraph(summary_text, ParagraphStyle(
            'SummaryBox',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=9.5,
            leading=14,
            textColor=colors.HexColor('#0B2545')
        )))

        # Conditional iPad Specification & Payment Note in PDF
        if len(full_ipad_pkg_students) > 0:
            elements.append(Spacer(1, 8))
            ipad_pdf_text = f"<b>iPad Package Specs & Terms:</b> Included for ({', '.join(full_ipad_pkg_students)}). Package includes iPad A16 128GB, Cover, Stylus, AppleCare+ Enterprise, Jamf MDM, Microsoft 365, and Apple Managed Services. <i>*SAR 2,800 offer valid only on instant payment (SAR 3,000 on 12-month installment). Software management licenses must be renewed annually.</i>"
            elements.append(Paragraph(ipad_pdf_text, ParagraphStyle(
                'IPadBox',
                parent=styles['Normal'],
                fontName='Helvetica-Oblique',
                fontSize=7.5,
                leading=10,
                textColor=colors.HexColor('#475569')
            )))
        
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
