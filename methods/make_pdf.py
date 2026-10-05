"""PDF profesional con fpdf2 (Arial TTF, cabecera con banda + logo, tablas).

Uso:
    pip install fpdf2 pillow
    python methods/make_pdf.py   # editar CONTENT y rutas

Salida: docs/informe.pdf
"""
from fpdf import FPDF

ARIAL = "C:/Windows/Fonts/arial.ttf"
ARIAL_B = "C:/Windows/Fonts/arialbd.ttf"
NAVY = (30, 58, 110)
BLUE = (0, 85, 136)          # #005588 (TVN)
LIGHT = (238, 244, 255)
GRAY = (110, 120, 140)
DARK = (42, 42, 42)
OUT = "docs/informe.pdf"


class PDF(FPDF):
    def header(self):
        if self.page_no() == 1:
            return
        self.set_font("Arial", "", 8); self.set_text_color(*GRAY)
        self.cell(0, 8, "Documento", align="L")
        self.cell(0, 8, "2026", align="R", new_x="LMARGIN", new_y="NEXT")
        self.ln(6)

    def footer(self):
        self.set_y(-14)
        self.set_font("Arial", "", 8); self.set_text_color(*GRAY)
        self.cell(0, 8, f"Pagina {self.page_no()}", align="C")


pdf = PDF(format="A4")
pdf.add_font("Arial", "", ARIAL)
pdf.add_font("Arial", "B", ARIAL_B)
pdf.set_auto_page_break(auto=True, margin=18)
pdf.add_page()
pdf.set_margins(18, 16, 18)


def para(text, size=10, style="", lh=5.4, color=DARK):
    pdf.set_x(pdf.l_margin)
    pdf.set_font("Arial", style, size)
    pdf.set_text_color(*color)
    pdf.multi_cell(0, lh, text, new_x="LMARGIN", new_y="NEXT")


def section(title):
    pdf.ln(2); pdf.set_x(pdf.l_margin)
    pdf.set_font("Arial", "B", 13); pdf.set_text_color(*NAVY)
    pdf.cell(0, 8, title, new_x="LMARGIN", new_y="NEXT")
    pdf.set_draw_color(*BLUE); pdf.set_line_width(0.6)
    y = pdf.get_y(); pdf.line(18, y, 42, y); pdf.ln(3)
    pdf.set_text_color(*DARK)


def table(headers, rows, widths):
    pdf.set_x(pdf.l_margin); pdf.set_font("Arial", "B", 9)
    pdf.set_fill_color(*NAVY); pdf.set_text_color(255, 255, 255)
    for h, w in zip(headers, widths):
        pdf.cell(w, 8, h, fill=True); pdf.cell(1, 8, "")
    pdf.ln(8); pdf.set_text_color(*DARK); pdf.set_font("Arial", "", 8.6)
    fill = False
    for row in rows:
        hs = [len(pdf.multi_cell(w - 2, 4.2, t, dry_run=True, output="LINES")) * 4.2 + 3
              for t, w in zip(row, widths)]
        h = max(hs)
        if pdf.get_y() + h > 278:
            pdf.add_page()
        x0, y0 = pdf.l_margin, pdf.get_y()
        pdf.set_fill_color(*(LIGHT if fill else (255, 255, 255)))
        pdf.rect(x0, y0, sum(widths) + len(widths) - 1, h, style="F")
        x = x0
        for t, w in zip(row, widths):
            pdf.set_xy(x, y0 + 1.5)
            pdf.multi_cell(w - 2, 4.2, t, new_x="RIGHT", new_y="NEXT"); x += w + 1
        pdf.set_xy(x0, y0 + h); fill = not fill
    pdf.ln(3)


# ---- Contenido (editar) ----
pdf.set_fill_color(*BLUE); pdf.rect(0, 0, 210, 34, style="F")
pdf.set_xy(18, 10); pdf.set_font("Arial", "B", 20); pdf.set_text_color(255, 255, 255)
pdf.cell(0, 9, "Titulo del documento", new_x="LMARGIN", new_y="NEXT")
pdf.set_y(42)
para("Subtítulo o resumen.", 11, "B")
section("1. Seccion")
para("Texto de ejemplo.")
table(["Columna", "Descripcion"], [["A", "Detalle A"], ["B", "Detalle B"]], [40, 132])

pdf.output(OUT)
print("PDF generado:", OUT, "paginas:", pdf.page_no())
