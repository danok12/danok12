"""Запасной предпросмотр листов средствами ezdxf - там, где нет AutoCAD.

PNG по листам: preview_list1.png, preview_list2.png, ... (те же имена, что даёт
vypusk_acad.py; окончательные DWG и PDF - только из AutoCAD, папка «Чертежи»).
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
                           lineweight_scaling=1.0,
                           min_dash_length=0.01)
page = layout.Page(420, 297, layout.Units.mm, margins=layout.Margins.all(0))
names = [n for n in doc.layouts.names_in_taborder() if n != "Model"]
for k, name in enumerate(names, start=1):
    psp = doc.paperspace(name)
    ctx = RenderContext(doc)
    ctx.set_current_layout(psp)
    be = PyMuPdfBackend()
    Frontend(ctx, be, config=cfg).draw_layout(psp)
    png = f"preview_list{k}.png"
    open(png, "wb").write(be.get_pixmap_bytes(page, fmt="png", dpi=dpi))
print("ok", stem, names)
