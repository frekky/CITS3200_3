/** Django multiple select, copyright Felix von Perger (2023) under Creative Commons license */
let padding = '                                                    ';

function MultipleSelect(container, items, initial, onSelect) {
    let self = this;
    this.onSelect = onSelect;
    initial = initial || [];
    this.items = items || [];
    this.selection = {}; // per item code: {selected: true/false, el: JQueryElement}
    this.active = false;
    this.lastClick = null;
    this.focusTimer = null;
    this.selectCallback = onSelect;
    this.selectionChanged = false;

    container.html('');
    this.divOuter = $('<div/>').addClass('multiple-select collapsed').appendTo(container);
    this.inputEl = $('<input type="text"/>').appendTo(this.divOuter);
    this.divDropdown = $('<div/>').addClass('ms-dropdown').appendTo(this.divOuter);

    function keepFocus() {
        if (!self.focusTimer) {
            self.focusTimer = window.setTimeout(() => {
                if (!self.active) return;
                self.inputEl.focus();
                self.focusTimer = null;
            }, 0);
        }
    }

    this.divOuter.on('mousedown', function(e) {
        if (self.active) keepFocus();
    });

    this.inputEl.on('keydown', function (e) {
        e.preventDefault();
    }).on('blur', function (e) {
        if (self.focusTimer) return;
        console.log('inputEl blur');
        if (self.active && !self.focusTimer) self.close();
    }).on('mousedown', function (e) {
        if (document.readyState !== 'complete') {
            e.preventDefault();
        }
    }).on('click', function (e) {
        if (self.active) self.close();
        else self.open();
    });

    this.divBtns = $('<div/>').addClass('buttons mb-1').appendTo(this.divDropdown);
    this.btnAll = $('<input type="button" class="bg-secondary"/>').val('All').appendTo(this.divBtns).on('click', (e) => {
        self.doSelectAll(true);
    });
    this.btnNone = $('<input type="button" class="bg-secondary"/>').val('None').appendTo(this.divBtns).on('click', (e) => {
        self.doSelectAll(false);
    });

    this.itemsDiv = $('<ul/>').appendTo(this.divDropdown);

    for (var itm of items) {
        let code = itm[0];
        let initSel = initial.includes(code);
        let el = $('<li/>').text(itm[1]).appendTo(this.itemsDiv);
        if (initSel) {
            el.addClass('selected-item');
        }

        this.selection[code] = {
            selected: initSel, // active includes temporary selection
            el: el,
            text: itm[1],
        };

        el.on('click', function(e) {
            // toggle selection of this item
            if (self.selection[code].selected = !self.selection[code].selected) {
                self.selection[code].el.addClass('selected-item');
            } else {
                self.selection[code].el.removeClass('selected-item');
            }
            self.selectionChanged = true;
            self.updateSelection();
        });
    }

    this.updateSelection();
}

MultipleSelect.prototype.doSelectAll = function (allState) {
    Object.values(this.selection).forEach((selItm) => {
        if (allState) {
            selItm.el.addClass('selected-item');
            selItm.selected = true;
        } else {
            selItm.el.removeClass('selected-item');
            selItm.selected = false;
        }
    });
    this.selectionChanged = true;
    this.updateSelection();
}

MultipleSelect.prototype.open = function () {
    this.divOuter.removeClass('collapsed');
    this.active = true;
    this.selectionChanged = false;
}

MultipleSelect.prototype.applySelection = function () {
    if (!this.selectCallback) return;
    let selectedItems = Object.entries(this.selection).filter(([_, {selected}]) => selected).map(([code, _]) => code);
    this.selectCallback(selectedItems) && this.close(false);
}

MultipleSelect.prototype.updateSelection = function() {
    let selectedTexts = Object.values(this.selection).filter(({selected}) => selected).map(({text}) => text);

    if (selectedTexts.length == 0) {
        this.inputEl.val("(none)"); // useless filter operation! select none always gives no results!
    } else if (selectedTexts.length == Object.keys(this.selection).length) {
        this.inputEl.val("All");
    } else {
        this.inputEl.val(selectedTexts.join(', '));
    }
}

MultipleSelect.prototype.close = function () {
    this.active = false;
    this.divOuter.addClass('collapsed');
    if (this.focusTimer) {
        window.clearTimeout(this.focusTimer);
        this.focusTimer = null;
    }
    
    this.updateSelection();
    if (this.selectionChanged) this.applySelection();
};

function loadMultipleSelectFilter(baseQuery, noItemsQuery, lookup, containerId, items, selected) {
    let container = $(containerId);
    $(function () {
        let ms = new MultipleSelect(container, items, selected, function (newSelected) {
            // construct query string based on selection
            if (newSelected.length == items.length) {
                window.location = window.location.pathname + baseQuery; // no filter (show all)
            } else if (newSelected.length > 0) {
                let amp = baseQuery === '?' ? '' : '&';
                window.location = window.location.pathname + baseQuery + amp + lookup + '=' + newSelected.join(',');
            } else {
                window.location = window.location.pathname + noItemsQuery; // filter for only null values
            }
        });
    });
}

function loadNumericRangeFilter(containerId, baseQuery, lookupGte, lookupLte) {
    let container = $(containerId);
    let gteEl = container.find('[name="gte"]'), lteEl = container.find('[name="lte"]');
    container.find('form').on('submit', (e) => {
        e.preventDefault();
        let qs = baseQuery;
        let gte = gteEl.val(), lte = lteEl.val();
        if (gte !== "") {
            qs += (qs.endsWith('?') ? '' : '&') + lookupGte + '=' + gte;
        }
        if (lte !== "") {
            qs += (qs.endsWith('?') ? '' : '&') + lookupLte + '=' + lte;
        }
        window.location = window.location.pathname + qs;
    }).on('reset', (e) => {
        e.preventDefault();
        window.location = window.location.pathname + baseQuery;
    })
}

/* from django-admin-rangefilter */
function filter_apply(event, qs_name){
    event.preventDefault();
    const $form = django.jQuery(event.target).closest('form');
    const query_string = $form.find('input#'+qs_name).val();
    const form_data = $form.serialize();
    const amp = query_string === "?" ? "" : "&";  // avoid leading ?& combination
    window.location = window.location.pathname + query_string + amp + form_data;
}
function filter_reset(event, qs_name){
    const $form = django.jQuery(event.target).closest('form');
    const query_string = $form.find('input#' + qs_name).val();
    window.location = window.location.pathname + query_string;
}