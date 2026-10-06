"""Предпросмотр листов (PDF + PNG) средствами ezdxf - для проверки вёрстки.

Все листы чертежа идут в один многостраничный PDF; PNG - по листу:
<имя>_preview.png (Лист 1), <имя>_list2_preview.png (Лист 2) и т. д.
"""
import sys
import ezdxf
import pymupdf
from ezdxf.addons.drawing import Frontend, RenderContext, layout, config
from ezdxf.addons.drawing.pymupdf import PyMuPdfBackend

src = sys.argv[1]
dpi = int(sys.argv[2]) if len(sys.argv) > 2 else 150
doc = ezdxf.readfile(src)
for lay in doc.layers:          # непечатаемый слой видового экрана иначе прячет и его содержимое
    lay.dxf.plot = 1
doc.layers.get("Видовой_экран").color = 7
stem = src.rsplit(".", 1)[0]
cfg = config.Configuration(background_policy=config.BackgroundPolicy.WHITE,
                           color_policy=config.ColorPolicy.COLOR,
                           lineweight_scaling=1.0)
page = layout.Page(420, 297, layout.Units.mm, margins=layout.Margins.all(0))
out = pymupdf.open()
names = [n for n in doc.layouts.names_in_taborder() if n != "Model"]
for k, name in enumerate(names, start=1):
    psp = doc.paperspace(name)
    ctx = RenderContext(doc)
    ctx.set_current_layout(psp)
    be = PyMuPdfBackend()
    Frontend(ctx, be, config=cfg).draw_layout(psp)
    out.insert_pdf(pymupdf.open("pdf", be.get_pdf_bytes(page, settings=layout.Settings(fit_page=False, scale=1))))
    png = stem + ("_preview.png" if k == 1 else f"_list{k}_preview.png")
    open(png, "wb").write(be.get_pixmap_bytes(page, fmt="png", dpi=dpi))
out.save(stem + ".pdf")
print("ok", stem, names)
