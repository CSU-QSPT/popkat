"""
.. module:: pkdata
   :synopsis:

.. moduleauthor:: Brad Reisfeld <brad.reisfeld@colostate.edu>
"""


from PyQt5.QtWidgets import QTreeView, QLineEdit, QWizardPage, QLabel, QGridLayout
from PyQt5.QtCore import QSortFilterProxyModel, Qt
from PyQt5.QtGui import QStandardItem, QStandardItemModel


from utils import shared, db_utils

SimInfo = shared.SimInfo()


class ModelParamsPage(QWizardPage):
    def __init__(self, parent=None, *args):
        super().__init__(parent, *args)
        self.w_current_state = {}
        self.setup_ui()

    def setup_ui(self):
        self.param_tree = QTreeView()
        self.param_tree.setAlternatingRowColors(True)
        self.param_model = LeafFilterProxyModel(self)
        self.param_model.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.param_model.setDynamicSortFilter(False)
        self.param_tree.setModel(self.param_model)
        self.param_model.dataChanged.connect(self.on_item_changed)
        self.setStyleSheet(
            """QTreeView::item:has-children {
                  color: #000080;
               }"""
        )

        self.search_label = QLabel("Search for parameters")
        self.search_text = QLineEdit()

        self.grid = QGridLayout()
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.addWidget(self.param_tree, 0, 0, 1, 2)
        self.grid.addWidget(self.search_label, 1, 0)
        self.grid.addWidget(self.search_text, 1, 1)

        self.setLayout(self.grid)
        self.setTitle("Model Parameters")

    def initializePage(self):
        self._sim_params = SimInfo.sim_params
        self._model_params = SimInfo.model_params
        self.sim_type = self._sim_params["sim_type"]
        self.base_model = self._create_param_model(self, self.sim_type)
        pdesc_col_index = self._pcol_map["description"]
        self.param_tree.setColumnHidden(pdesc_col_index, True)
        self.param_model.setFilterKeyColumn(pdesc_col_index)
        self.search_text.textChanged.connect(self.param_model.setFilterRegExp)
        self.param_model.setSourceModel(self.base_model)
        self.sim_id = SimInfo.sim_geninfo["sim_id"]

    def validatePage(self):
        # do some additional validation

        # ... and write values to the shared structure
        self.save_to_shared()
        self.save_to_db()
        return True

    def save_to_shared(self):
        SimInfo.model_params = self._model_params

    def save_to_db(self):
        db = SimInfo.db_info["database"]["db"]
        # save to mysims
        table_name = SimInfo.db_info["tables"]["mysims"]["name"]
        update_map = {"model_params": self._model_params}
        db_utils.update_record(db, table_name, self.sim_id, update_map)

    def _create_param_model(self, parent, sim_type):
        model_params = self._model_params
        # sim types for which parameters need a checkbox selection
        self.est_type = sim_type in ["mcmc", "mcmc+setpts"]
        self.sens_type = sim_type in ["sensitivity"]
        col_keys = [
            "pname",
            "is_editable",
            "has_tooltip",
            "has_checkmark",
            "must_validate",
            "col_num",
        ]
        col_props = [
            ("name", False, True, True, False, 0),
            ("value", True, False, False, True, 1),
            ("units", False, False, False, False, 2),
            ("notes", True, False, False, False, 3),
            ("description", False, False, False, False, 4),
        ]

        self.varlabel_key = "name"

        col_map = {pnm: cnum for (cnum, pnm) in enumerate(col_keys)}
        self.cname_to_colnum = {c[0]: c[-1] for c in col_props}
        self.colnum_to_cname = {c[-1]: c[0] for c in col_props}

        model = QStandardItemModel()
        # order with respect to col_num and select the pname
        pname, col_num = col_map["pname"], col_map["col_num"]
        headers = [p[pname] for p in sorted(col_props, key=lambda x: x[col_num])]
        model.setHorizontalHeaderLabels(headers)
        self._pcol_map = {h: i for (i, h) in enumerate(headers)}
        param_class_names = model_params.keys()

        tooltip_field = "description"

        self._widget_map = {}
        for class_name in param_class_names:
            params = model_params[class_name]
            param_class = QStandardItem(class_name)
            param_class.setFlags(Qt.NoItemFlags)
            param_class.setFlags(param_class.flags() & ~Qt.ItemIsSelectable)
            for param in params:
                param_row = []
                for_estimation = param["for_estimation"]
                for_sensitivity = param["for_sensitivity"]
                tooltip = param[tooltip_field]
                for val in col_props:
                    (
                        pname,
                        is_editable,
                        has_tooltip,
                        has_checkmark,
                        must_validate,
                        col,
                    ) = val
                    p = QStandardItem()
                    p.setText(param[pname])
                    p.setEditable(is_editable)
                    if has_tooltip:
                        p.setToolTip(tooltip)
                    if must_validate:
                        pass
                    if has_checkmark:
                        p.setFlags(p.flags() | Qt.ItemIsUserCheckable)
                        p.setCheckable(True)
                        if (for_estimation and self.est_type) or (
                            for_sensitivity and self.sens_type
                        ):
                            p.setCheckState(Qt.Checked)
                        else:
                            p.setCheckState(Qt.Unchecked)
                        pval = param[self.varlabel_key]
                        self._widget_map[pval] = p
                    param_row.insert(col, p)
                param_class.appendRow(param_row)
            model.appendRow(param_class)
        return model

    def on_item_changed(self, index):
        """Update underlying datastructure when item in view is changed"""
        model = self.param_tree.model()

        # determine which param field was edited
        row, col, parent = index.row(), index.column(), index.parent()
        pkey = self.colnum_to_cname[col]

        # find the name of the parameter that was edited
        pname_col = self.cname_to_colnum[self.varlabel_key]

        # get information to be able to index back into our datastructure
        pclass = parent.data()
        pname = model.data(model.index(row, pname_col, parent), Qt.EditRole)

        # get the new value
        new_val = index.data()

        # set the value in the datastructure for this page
        locator = {"pclass": pclass, "pname": pname, "pkey": pkey}
        self.set_in_datastruct(self._model_params, locator, new_val)

    def get_from_datastruct(self, param_data, locator):
        pclass, pname, pkey = [locator[x] for x in ("pclass", "pname", "pkey")]
        param_list = param_data[pclass]
        for param in param_list:
            if param[self.varlabel_key] == pname:
                val = param[pkey]
        return val

    def set_in_datastruct(self, param_data, locator, pval):
        """This is essentially an indexer that will put an entry in the
        appropriate place in the underlying data structure"""
        pclass, pname, pkey = [locator[x] for x in ("pclass", "pname", "pkey")]
        param_list = param_data[pclass]
        # pkey is one of the writable columns, e.g., 'name', 'notes',
        for param in param_list:
            if param[self.varlabel_key] == pname:
                param[pkey] = pval
            # need to detect the state of the checkmark and potentially update
            # 'for_estimation' or 'for_sensitivity'
            if pkey == "name":
                widget = self._widget_map[pval]
                is_checked = widget.checkState() == Qt.Checked
                if self.est_type:
                    param["for_estimation"] = is_checked
                if self.sens_type:
                    param["for_sensitivity"] = is_checked


class LeafFilterProxyModel(QSortFilterProxyModel):
    """ Class to override the following behaviour:
            If a parent item doesn't match the filter,
            none of its children will be shown.

        This Model matches items which are descendants
        or ascendants of matching items.
    """

    def filterAcceptsRow(self, row_num, source_parent):
        """ Overriding the parent function """

        # Check if the current row matches
        if self.filter_accepts_row_itself(row_num, source_parent):
            return True

        # Traverse up all the way to root and check if any of them match
        if self.filter_accepts_any_parent(source_parent):
            return True

        # Finally, check if any of the children match
        return self.has_accepted_children(row_num, source_parent)

    def filter_accepts_row_itself(self, row_num, parent):
        return super(LeafFilterProxyModel, self).filterAcceptsRow(row_num, parent)

    def filter_accepts_any_parent(self, parent):
        """ Traverse to the root node and check if any of the
            ancestors match the filter
        """
        while parent.isValid():
            if self.filter_accepts_row_itself(parent.row(), parent.parent()):
                return True
            parent = parent.parent()
        return False

    def has_accepted_children(self, row_num, parent):
        """ Starting from the current node as root, traverse all
            the descendants and test if any of the children match
        """
        model = self.sourceModel()
        source_index = model.index(row_num, 0, parent)

        children_count = model.rowCount(source_index)
        for i in range(children_count):
            if self.filterAcceptsRow(i, source_index):
                return True
        return False
