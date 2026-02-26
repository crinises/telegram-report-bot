import pandas as pd
import io
import os
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from groq import Groq
from dotenv import load_dotenv
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


load_dotenv()

pdfmetrics.registerFont(TTFont("Arial", "fonts/arial.ttf"))
pdfmetrics.registerFont(TTFont("Arial-Bold", "fonts/arialbd.ttf"))

FONT = "Arial"
FONT_BOLD = "Arial-Bold"


TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

client = Groq(api_key=os.getenv("GROQ_API_KEY"))



pending_files = {}


def detect_header_and_clean(df_raw):
    header_row = 0
    for i, row in df_raw.iterrows():
        non_null = row.dropna()
        if len(non_null) >= max(3, len(df_raw.columns) * 0.5):
            header_row = i
            break
    df = df_raw.iloc[header_row + 1:].copy()
    df.columns = df_raw.iloc[header_row].tolist()
    df = df.dropna(how='all').reset_index(drop=True)
    df = df[[c for c in df.columns if str(c) != 'nan']]
    return df


def generate_pdf(sheets, ai_analysis, title="Raport"):
    filename = "raport.pdf"
    doc = SimpleDocTemplate(
        filename, pagesize=A4,
        rightMargin=1.5*cm, leftMargin=1.5*cm,
        topMargin=1.5*cm, bottomMargin=1.5*cm
    )

    title_style = ParagraphStyle(
        'CustomTitle', fontName=FONT_BOLD, fontSize=22,
        textColor=colors.HexColor('#1a1a2e'), spaceAfter=20, alignment=1
    )
    subtitle_style = ParagraphStyle(
        'Subtitle', fontName=FONT, fontSize=10,
        textColor=colors.HexColor('#666666'), spaceAfter=16, alignment=1
    )
    heading_style = ParagraphStyle(
        'Heading', fontName=FONT_BOLD, fontSize=13,
        textColor=colors.HexColor('#1a1a2e'), spaceBefore=14, spaceAfter=8
    )
    sheet_heading_style = ParagraphStyle(
        'SheetHeading', fontName=FONT_BOLD, fontSize=11,
        textColor=colors.HexColor('#16213e'), spaceBefore=10, spaceAfter=6
    )
    subheading_style = ParagraphStyle(
        'SubHeading', fontName=FONT_BOLD, fontSize=11,
        textColor=colors.HexColor('#1a1a2e'), spaceBefore=10, spaceAfter=6
    )
    body_style = ParagraphStyle(
        'Body', fontName=FONT, fontSize=9,
        leading=15, spaceAfter=6, textColor=colors.HexColor('#333333')
    )

    cell_header = ParagraphStyle('CH', fontName=FONT_BOLD, fontSize=9, textColor=colors.white, alignment=1)
    cell_label = ParagraphStyle('CL', fontName=FONT, fontSize=9, textColor=colors.HexColor('#333333'))
    cell_value = ParagraphStyle('CV', fontName=FONT, fontSize=9, textColor=colors.HexColor('#333333'), alignment=2)
    cell_label_wrap = ParagraphStyle('CLW', fontName=FONT, fontSize=9, textColor=colors.HexColor('#333333'), leading=13)
    cell_col_name = ParagraphStyle('CCN', fontName=FONT_BOLD, fontSize=9, textColor=colors.HexColor('#1a1a2e'))

    elements = []

    elements.append(Paragraph(title, title_style))
    elements.append(Paragraph(datetime.now().strftime('%d.%m.%Y %H:%M'), subtitle_style))
    elements.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor('#1a1a2e'), spaceAfter=16))

    # sumar general
    elements.append(Paragraph("1. Sumar Date", heading_style))

    total_rows = sum(len(df) for df in sheets.values())
    sheet_names = ", ".join(sheets.keys())

    general_data = [
        [Paragraph("Parametru", cell_header), Paragraph("Valoare", cell_header)],
        [Paragraph("Total sheet-uri", cell_label), Paragraph(str(len(sheets)), cell_value)],
        [Paragraph("Sheet-uri", cell_label), Paragraph(sheet_names, cell_label_wrap)],
        [Paragraph("Total randuri (toate sheet-urile)", cell_label), Paragraph(str(total_rows), cell_value)],
    ]

    general_table = Table(general_data, colWidths=[7*cm, 10.5*cm])
    general_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a1a2e')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#f0f4ff'), colors.white]),
        ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#cccccc')),
        ('PADDING', (0, 0), (-1, -1), 8),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    elements.append(general_table)
    elements.append(Spacer(1, 0.4*cm))

    elements.append(Paragraph("2. Detalii per Sheet", heading_style))

    for sheet_name, df in sheets.items():
        elements.append(Paragraph(f"Sheet: {sheet_name}", sheet_heading_style))

        sheet_summary = [
            [Paragraph("Parametru", cell_header), Paragraph("Valoare", cell_header)],
            [Paragraph("Randuri", cell_label), Paragraph(str(len(df)), cell_value)],
            [Paragraph("Coloane", cell_label), Paragraph(str(len(df.columns)), cell_value)],
            [Paragraph("Coloane disponibile", cell_label),
             Paragraph(", ".join(str(c) for c in df.columns.tolist()), cell_label_wrap)],
        ]

        sheet_table = Table(sheet_summary, colWidths=[7*cm, 10.5*cm])
        sheet_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#16213e')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#f0f4ff'), colors.white]),
            ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#cccccc')),
            ('PADDING', (0, 0), (-1, -1), 8),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        elements.append(sheet_table)
        elements.append(Spacer(1, 0.2*cm))

        numeric_cols = df.select_dtypes(include='number').columns.tolist()
        if numeric_cols:
            col_w_stats = 17.5*cm / 5
            stats_data = [
                [
                    Paragraph("Coloana", cell_header),
                    Paragraph("Medie", cell_header),
                    Paragraph("Maxim", cell_header),
                    Paragraph("Minim", cell_header),
                    Paragraph("Suma", cell_header),
                ]
            ]
            for col in numeric_cols:
                col_clean = df[col].dropna()
                if len(col_clean) > 0:
                    stats_data.append([
                        Paragraph(str(col), cell_col_name),
                        Paragraph(f"{col_clean.mean():,.2f}", cell_value),
                        Paragraph(f"{col_clean.max():,.2f}", cell_value),
                        Paragraph(f"{col_clean.min():,.2f}", cell_value),
                        Paragraph(f"{col_clean.sum():,.2f}", cell_value),
                    ])
            stats_table = Table(stats_data, colWidths=[col_w_stats]*5)
            stats_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#16213e')),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#f0f4ff'), colors.white]),
                ('BACKGROUND', (0, 1), (0, -1), colors.HexColor('#e8ecff')),
                ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#cccccc')),
                ('PADDING', (0, 0), (-1, -1), 8),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            elements.append(stats_table)
            elements.append(Spacer(1, 0.3*cm))

    elements.append(Paragraph("3. Date Originale (primele 20 randuri per sheet)", heading_style))

    page_width = A4[0] - 3*cm

    for sheet_name, df in sheets.items():
        elements.append(Paragraph(f"Sheet: {sheet_name}", sheet_heading_style))

        num_cols = len(df.columns)
        if num_cols == 0:
            continue
        col_w = page_width / num_cols

        header_row = [
            Paragraph(str(c), ParagraphStyle('TH', fontName=FONT_BOLD, fontSize=7,
                                              textColor=colors.white, alignment=1))
            for c in df.columns.tolist()
        ]
        table_data = [header_row]
        for _, row in df.head(20).iterrows():
            table_data.append([
                Paragraph(
                    str(v) if str(v) != 'nan' else '-',
                    ParagraphStyle('TD', fontName=FONT, fontSize=7,
                                   textColor=colors.HexColor('#333333'), alignment=1)
                )
                for v in row.tolist()
            ])

        data_table = Table(table_data, colWidths=[col_w]*num_cols)
        data_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#16213e')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#f9f9f9'), colors.white]),
            ('GRID', (0, 0), (-1, -1), 0.3, colors.HexColor('#dddddd')),
            ('PADDING', (0, 0), (-1, -1), 4),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        elements.append(data_table)
        elements.append(Spacer(1, 0.4*cm))


    elements.append(Paragraph("4. Analiza specialistului", heading_style))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#cccccc'), spaceAfter=10))

    clean_text = (ai_analysis
                  .replace('**', '').replace('*', '').replace('#', '')
                  .replace('\n', '<br/>'))
    elements.append(Paragraph(clean_text, body_style))

    elements.append(Spacer(1, 1*cm))
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#1a1a2e'), spaceBefore=8))
    elements.append(Paragraph(
        "Report Generator — Celestia reserved rights",
        ParagraphStyle('Footer', fontName=FONT, fontSize=8,
                       textColor=colors.HexColor('#999999'), alignment=1)
    ))

    doc.build(elements)
    return filename


async def analyze_with_ai_multi(sheets: dict):
    full_stats = ""

    for sheet_name, df in sheets.items():
        full_stats += f"\n{'='*40}\nSHEET: {sheet_name}\n{'='*40}\n"
        full_stats += f"Randuri: {len(df)}, Coloane: {len(df.columns)}\n"
        full_stats += f"Coloane: {', '.join(str(c) for c in df.columns.tolist())}\n\n"

        try:
            sample = df.head(4).to_string(index=False)
            full_stats += f"Primele 4 randuri:\n{sample}\n\n"
        except Exception:
            pass

        for col in df.select_dtypes(include='number').columns:
            col_clean = df[col].dropna()
            if len(col_clean) > 0:
                full_stats += f"- {col}: medie={col_clean.mean():.2f}, max={col_clean.max():.2f}, min={col_clean.min():.2f}, suma={col_clean.sum():.2f}\n"

        for col in df.select_dtypes(include='object').columns:
            unique_vals = df[col].dropna().unique()
            if len(unique_vals) <= 15:
                full_stats += f"- {col} (valori): {', '.join(str(v) for v in unique_vals)}\n"
            else:
                full_stats += f"- {col}: {len(unique_vals)} valori unice\n"

    if len(full_stats) > 6000:
        full_stats = full_stats[:6000] + "\n[... date trunchiate pentru analiza]"

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{
            "role": "user",
            "content": (
                "Esti un analist de date senior cu 20 de ani experienta in domeniu.\n\n"
                "Analizeaza datele din TOATE sheet-urile de mai jos si:\n"
                "1. Identifica tipul de date si domeniul (audit, financiar, HR, etc.)\n"
                "2. Analizeaza fiecare sheet separat cu concluzii specifice\n"
                "3. Include: concluzii cheie, tendinte, anomalii, valori extreme, recomandari concrete ceea ce un specialist ar sugera\n"
                "4. La final scrie o concluzie generala care leaga toate sheet-urile\n\n"
                f"Date:\n{full_stats}"
            )
        }]
    )
    return response.choices[0].message.content


async def process_report(message, user_id, title, file_data):
    try:
        if file_data["filename"].endswith('.xlsx'):
            all_sheets_raw = pd.read_excel(io.BytesIO(file_data["bytes"]), sheet_name=None, header=None)
        else:
            raw = pd.read_csv(io.BytesIO(file_data["bytes"]), header=None)
            all_sheets_raw = {"Sheet1": raw}
    except Exception as e:
        await message.reply_text(f"Eroare la citirea fisierului: {str(e)}")
        return

    cleaned_sheets = {}
    for sheet_name, df_raw in all_sheets_raw.items():
        try:
            df = detect_header_and_clean(df_raw)
            if len(df) > 0 and len(df.columns) > 0:
                cleaned_sheets[sheet_name] = df
        except Exception:
            continue

    if not cleaned_sheets:
        await message.reply_text("Nu am putut citi datele din fisier. Verifica formatul!")
        return

    sheet_info = ", ".join(f"{k} ({len(v)} randuri)" for k, v in cleaned_sheets.items())
    await message.reply_text(
        f"Fisier cu {len(cleaned_sheets)} sheet-uri detectate:\n{sheet_info}\n\nAnalizez toate datele..."
    )

    try:
        ai_analysis = await analyze_with_ai_multi(cleaned_sheets)
    except Exception as e:
        await message.reply_text(f"Eroare : {str(e)}")
        return

    await message.reply_text("Generez raportul PDF...")

    pdf_path = generate_pdf(cleaned_sheets, ai_analysis, title)

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Regenereaza", callback_data="regenerate"),
            InlineKeyboardButton("Schimba titlul", callback_data="change_title")
        ]
    ])

    pending_files[user_id] = {**file_data, "title": title}

    with open(pdf_path, 'rb') as pdf_file:
        await message.reply_document(
            document=pdf_file,
            filename=f"{title}.pdf",
            caption=f"{title} — generat cu succes.",
            reply_markup=keyboard
        )
    os.remove(pdf_path)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = ReplyKeyboardMarkup(
        [["Start — Trimite fisier"]],
        resize_keyboard=True,
        is_persistent=True
    )
    await update.message.reply_text(
        "Salut! Sunt un agent pentru generarea rapoartelor.\n\n"
        "Trimite-mi un fisier Excel (.xlsx) sau CSV (.csv) si iti generez automat un raport PDF profesional cu analiza detaliata.\n\n"
        "Datele tale sunt procesate local si nu sunt stocate sau trimise nicaieri in afara analizei. "
        "Fisierul tau este sters automat dupa generarea raportului.\n\n"
        "Created by Celestia",
        reply_markup=keyboard
    )


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file = update.message.document
    filename = file.file_name

    if not (filename.endswith('.xlsx') or filename.endswith('.csv')):
        await update.message.reply_text("Trimite doar fisiere .xlsx sau .csv!")
        return

    new_file = await context.bot.get_file(file.file_id)
    file_bytes = await new_file.download_as_bytearray()

    user_id = update.message.from_user.id
    pending_files[user_id] = {
        "bytes": file_bytes,
        "filename": filename
    }

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Omite — titlu automat", callback_data="skip_title")]
    ])

    await update.message.reply_text(
        "Fisier primit!\n\n"
        "Datele tale sunt procesate doar pentru generarea raportului si nu sunt salvate sau partajate.\n\n"
        "Scrie titlul raportului tau:\n"
        "_(ex: Raport Vanzari Q1 2026, Analiza Financiara, etc.)_\n\n"
        "Sau apasa Omite pentru titlu automat.",
        parse_mode="Markdown",
        reply_markup=keyboard
    )


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if query.data == "skip_title":
        if user_id not in pending_files:
            await query.message.reply_text("Trimite mai intai un fisier!")
            return
        file_data = pending_files[user_id]
        title = file_data["filename"].replace(".xlsx", "").replace(".csv", "")
        await query.edit_message_text(f"Titlu automat: {title}\nGenerez raportul...")
        await process_report(query.message, user_id, title, file_data)

    elif query.data == "regenerate":
        if user_id not in pending_files:
            await query.message.reply_text("Nu am fisierul salvat. Trimite-l din nou!")
            return
        file_data = pending_files[user_id]
        title = file_data.get("title", "Raport")
        try:
            await query.edit_message_caption(f"Regenerez raportul: {title}...")
        except Exception:
            pass
        await process_report(query.message, user_id, title, file_data)

    elif query.data == "change_title":
        if user_id in pending_files:
            pending_files[user_id]["waiting_new_title"] = True
        await query.message.reply_text("Scrie noul titlu pentru raport:")


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text

    if text == "Start — Trimite fisier":
        await update.message.reply_text(
            "Trimite-mi un fisier Excel (.xlsx) sau CSV (.csv)!"
        )
        return

    if user_id in pending_files:
        file_data = pending_files[user_id]

        if file_data.get("waiting_new_title"):
            title = text
            file_data["title"] = title
            file_data["waiting_new_title"] = False
            pending_files[user_id] = file_data
            await update.message.reply_text(
                f"Titlu nou: *{title}*\nRegenerez raportul...",
                parse_mode="Markdown"
            )
            await process_report(update.message, user_id, title, file_data)
            return

        title = text
        file_data_copy = pending_files.pop(user_id)
        await update.message.reply_text(
            f"Generez raportul: *{title}*...",
            parse_mode="Markdown"
        )
        await process_report(update.message, user_id, title, file_data_copy)

    else:
        await update.message.reply_text(
            "Trimite un fisier Excel (.xlsx) sau CSV (.csv) si iti generez un raport PDF!"
        )


app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(button_callback))
app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

print("Botul pentru rapoarte a pornit!")
app.run_polling()