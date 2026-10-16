"""Capture six pages in two themes with fixed time and isolated synthetic storage.

Usage: python tools/capture_ui_snapshot.py SOURCE_DIRECTORY OUTPUT_JSON
Run in a fresh process per source tree with QT_QPA_PLATFORM=offscreen.
"""
import gc,json,pathlib,sys,tempfile
from PySide6.QtCore import QCoreApplication, QEvent
from datetime import datetime
from PySide6.QtWidgets import QApplication,QWidget,QLabel,QAbstractButton,QLineEdit,QComboBox,QTableWidget,QTabWidget
sys.path.insert(0,sys.argv[1])
import app.core.paths as paths
runtime=tempfile.TemporaryDirectory()
paths.runtime_root=lambda:pathlib.Path(runtime.name)
import app.ui.main_window as mw
import app.services.periodicals as periodicals
periodicals.runtime_root = lambda: pathlib.Path(runtime.name)
class FixedDatetime(datetime):
 @classmethod
 def now(cls,tz=None):return cls(2026,10,16,12,30,0)
for module_name, module in list(sys.modules.items()):
 if module_name.startswith("app.") and getattr(module, "datetime", None) is datetime:
  module.datetime = FixedDatetime
app=QApplication([]); win=mw.MainWindow();win.showMaximized();app.processEvents()
def capture():
 data=[]
 for widget in [win,*win.findChildren(QWidget)]:
  item={'class':type(widget).__name__,'name':widget.objectName(),'visible':widget.isVisible(),'enabled':widget.isEnabled(),'geometry':[widget.x(),widget.y(),widget.width(),widget.height()]}
  if isinstance(widget,(QLabel,QAbstractButton,QLineEdit)):item['text']=widget.text()
  if isinstance(widget,QAbstractButton):item['checked']=widget.isChecked()
  if isinstance(widget,QComboBox):item['items']=[widget.itemText(i) for i in range(widget.count())]
  if isinstance(widget,QTableWidget):item['columns']=[widget.horizontalHeaderItem(i).text() if widget.horizontalHeaderItem(i) else '' for i in range(widget.columnCount())]
  if isinstance(widget,QTabWidget):item['tabs']=[widget.tabText(i) for i in range(widget.count())]
  data.append(item)
 return data
out={}
for theme in ('dark','light'):
 win.theme_name=theme;win.apply_theme()
 for name in ('fines','refusals','daily','periodics','people','receipts'):
  win.show_page(name);app.processEvents();out[theme+'/'+name]=capture()
pathlib.Path(sys.argv[2]).write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n', encoding='utf-8')
win.timer.stop()
win.close()
win.deleteLater()
QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
app.processEvents()
del win
gc.collect()
runtime.cleanup()
print('Captured',len(out),'views')
