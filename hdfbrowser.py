import sys
from collections import OrderedDict
import numpy as np
import pyqtgraph as pg
import pyqtgraph.console
from pyqtgraph.Qt import QtGui, QtCore, QtWidgets
import h5py
import hdf5

# changed in PyQt6
if 'Horizontal' not in dir(QtCore.Qt):
    QtCore.Qt.Horizontal = QtCore.Qt.Orientation.Horizontal
    QtCore.Qt.Vertical = QtCore.Qt.Orientation.Vertical


class HdfBrowser(QtWidgets.QSplitter):
    def __init__(self):
        # Use Qt::Horizontal
        QtWidgets.QSplitter.__init__(self, QtCore.Qt.Horizontal)

        self.left_split = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        self.addWidget(self.left_split)

        self.right_split = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        self.addWidget(self.right_split)

        self.tree = HdfTree()
        self.left_split.addWidget(self.tree)

        self.meta_table = HdfMetaTable()
        self.left_split.addWidget(self.meta_table)

        self.left_split.setSizes([400, 300])

        self.data_view = HdfDataView()
        self.right_split.addWidget(self.data_view)

        self.console = pg.console.ConsoleWidget(text="""
        Console variables:
          hdf : the currently loaded h5py file object
          sel : the currently selected object from the browser tree

        Double-click on a tree item to paste its variable name into the console input.
        """)
        self.right_split.addWidget(self.console)

        self.setSizes([200, 800])
        self.right_split.setSizes([600, 200])
        self.resize(1200, 800)

        self.tree.itemSelectionChanged.connect(self.tree_item_selected)
        self.tree.itemDoubleClicked.connect(self.tree_item_double_clicked)

    def load_file(self, filename):
        self.hdf = h5py.File(filename)
        self.console.localNamespace['hdf'] = self.hdf
        self.tree.set_root_hdf(self.hdf)
        self.setWindowTitle(filename)

    def tree_item_selected(self):
        sel = self.tree.selectedItems()
        if len(sel) == 0:
            self.meta_table.clear()
            self.data_view.clear()
            self.console.localNamespace['sel'] = None
        else:
            self.meta_table.set_hdf(sel[0].hdf)
            try:
                self.data_view.set_hdf(sel[0].hdf)
            except Exception:
                sys.excepthook(*sys.exc_info())
            self.console.localNamespace['sel'] = sel[0].hdf

    def tree_item_double_clicked(self, item, col):
        extra = "hdf['{}']".format(item.hdf.name)
        self.console.input.setText(self.console.input.text() + extra)


class HdfTree(pg.TreeWidget):
    def __init__(self, parent=None):
        self._hdf = None
        pg.TreeWidget.__init__(self, parent)
        self.setHeaderHidden(True)
        self.itemExpanded.connect(self.item_expanded)

    def set_root_hdf(self, hdf):
        self.hdf = hdf
        self.clear()
        self.root_tree_item = HdfTreeItem(self.hdf)
        self.addTopLevelItem(self.root_tree_item)
        self.root_tree_item.setExpanded(True)

    def expand_all(self):
        self.root_tree_item.expand_all()

    def item_expanded(self, item):
        item.expanded()


class HdfTreeItem(pg.TreeWidgetItem):
    def __init__(self, hdf):
        self.hdf = hdf

        name = hdf.name
        parent = hdf.parent
        if parent is not hdf:
            name = name[len(parent.name.rstrip('/'))+1:]
            

        pg.TreeWidgetItem.__init__(self, [name])
        if isinstance(hdf, h5py.Group) and len(self.hdf.keys()) > 0:
            self._loading_item = pg.TreeWidgetItem(["loading.."])
            self.addChild(self._loading_item)
            self._children_loaded = False
        else:
            self._loading_item = None
            self._children_loaded = True

    def expanded(self):
        # make sure children have been loaded
        self._load_children()

    def expand_all(self):
        self.setExpanded(True)
        for i in range(self.childCount()):
            self.child(i).expand_all()

    def _load_children(self):
        if self._children_loaded:
            return
        self.removeChild(self._loading_item)
        for hdf in self.hdf.values():
            ch = HdfTreeItem(hdf)
            self.addChild(ch)
        self._children_loaded = True


class HdfMetaTable(pg.DataTreeWidget):
    def __init__(self):
        pg.DataTreeWidget.__init__(self)

    def set_hdf(self, hdf):
        self.hdf = hdf  
        meta = OrderedDict()
        meta['type'] = type(hdf)
        if isinstance(hdf, h5py.Dataset):
            meta['dtype'] = hdf.dtype
            meta['shape'] = hdf.shape
            meta['chunks'] = hdf.chunks
            meta['compression'] = hdf.compression
            meta['compression_opts'] = hdf.compression_opts
            meta['scaleoffset'] = hdf.scaleoffset

        attrs = {}
        for k in hdf.attrs:
            try:
                attrs[k] = hdf.attrs[k]
            except Exception as err:
                if str(err).startswith("Unable to read attribute"):
                    try:
                        # try a different method for reading some attributes
                        #  see: https://github.com/h5py/h5py/issues/585
                        attrs[k] = hdf5.read_str_attribute(hdf._id.id, k)
                        continue
                    except Exception:
                        pass
                attrs[k] = str(err)

        meta['attributes'] = attrs
        self.setData(meta)


class HdfDataView(QtWidgets.QStackedWidget):
    def __init__(self):
        QtWidgets.QStackedWidget.__init__(self)
        self.widgets = {}
        self.widgets['empty'] =  QtWidgets.QWidget()
        self.widgets['table'] = pg.TableWidget()
        self.widgets['text'] = QtWidgets.QTextBrowser()
        self.widgets['plot'] = pg.PlotWidget()
        self.widgets['image'] = pg.ImageView()

        for w in self.widgets.values():
            self.addWidget(w)
        self.clear()

    def set_hdf(self, hdf):
        self.hdf = hdf
        if isinstance(hdf, h5py.Dataset):
            arr = np.array(hdf)
            if arr.ndim == 0 or arr.size <= 1:
                self.set_mode('text')
            elif arr.ndim == 1:
                self.set_mode('plot')
            elif arr.ndim == 2:
                self.set_mode('image')
            else:
                self.set_mode('text')
        else:
            self.set_mode('empty')

    def clear(self):
        self.set_mode('empty')

    def set_mode(self, mode):
        self.setCurrentWidget(self.widgets[mode])
        if mode == 'empty':
            return
        arr = np.asarray(self.hdf)
        try:
            if mode == 'plot':
                self.widgets['plot'].plot(arr, clear=True)
            elif mode == 'image':
                self.widgets['image'].setImage(arr)
            elif mode == 'text':
                self.widgets['text'].setPlainText(str(arr))
        except:
            print(type(arr))
            raise


if __name__ == '__main__':
    import os, sys
    app = pg.mkQApp()

    filename = None
    default_path = os.path.abspath('.')
    if len(sys.argv) > 1:
        filename = sys.argv[1]
        if os.path.isdir(filename):
            default_path = filename
            filename = None

    if filename is None:
        filters = "HDF5 files (*.h5);;All files (*.*)"
        filename = str(pg.Qt.QtWidgets.QFileDialog.getOpenFileName(None, "Open HDF5 file", default_path, filters))
        if filename == '':
            sys.exit(0)
    
    browser = HdfBrowser()
    browser.show()
    browser.load_file(filename)
    browser.tree.expand_all()

    if sys.flags.interactive == 0:
        try:
            app.exec_()
        except AttributeError:
            app.exec()

