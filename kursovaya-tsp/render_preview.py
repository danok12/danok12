"""Предпросмотр листа (PDF + PNG) средствами ezdxf - для проверки вёрстки."""
import sys
import ezdxf
from ezdxf.addons.drawing import Frontend, RenderContext, layout, config
from ezdxf.addons.drawing.pymupdf import PyMuPdfBackend

src = sys.argv[1]
doc = ezdxf.readfile(src)
psp = doc.paperspace("Лист 1")
for lay in doc.layers:          # непечатаемый слой видового экрана иначе прячет и его содержимое
    lay.dxf.plot = 1
vp_layer = doc.layers.get("Видовой_экран")
vp_layer.color = 7
ctx = RenderContext(doc)
ctx.set_current_layout(psp)
be = PyMuPdfBackend()
cfg = config.Configuration(background_policy=config.BackgroundPolicy.WHITE,
                           color_policy=config.ColorPolicy.COLOR,
                           lineweight_scaling=1.0)
Frontend(ctx, be, config=cfg).draw_layout(psp)
page = layout.Page(420, 297, layout.Units.mm, margins=layout.Margins.all(0))
stem = src.rsplit(".", 1)[0]
open(stem + ".pdf", "wb").write(be.get_pdf_bytes(page, settings=layout.Settings(fit_page=False, scale=1)))
open(stem + "_preview.png", "wb").write(be.get_pixmap_bytes(page, fmt="png", dpi=int(sys.argv[2]) if len(sys.argv) > 2 else 150))
print("ok", stem)
