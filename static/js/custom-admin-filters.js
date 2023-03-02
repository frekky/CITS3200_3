/** Django multiple select, copyright Felix von Perger (2023) under Creative Commons license */

function MultipleSelect(container, items, initial, onSelect) {
    let self = this;
    this.onSelect = onSelect;
    initial = initial || [];
    this.items = items || [];
    this.selection = {}; // per item code: {selected: true/false, el: JQueryElement}
    this.active = false;

    container.html('');
    this.divOuter = $('<div/>').addClass('multiple-select form-control collapsed').appendTo(container);

    this.divOuter.on('click', function(e) {
        console.log('ul click');
        if (!self.active) {
            self.open();
        }
    });

    this.divSelectBtns = $('<div/>').addClass('buttons mb-1').appendTo(this.divOuter);
    this.btnAll = $('<input type="button"/>').val('All').appendTo(this.divSelectBtns).on('click', (e) => {
        e.stopPropagation();
        self.doSelectAll(true);
    });
    this.btnNone = $('<input type="button"/>').val('None').appendTo(this.divSelectBtns).on('click', (e) => {
        e.stopPropagation();
        self.doSelectAll(false);
    });
    this.itemsDiv = $('<div class="item-container"/>').appendTo(this.divOuter);

    var numSelected = 0;
    for (var itm of items) {
        let code = itm[0];
        let initSel = initial.includes(code);
        if (initSel) numSelected++;
        let el = $('<div class="item"/>').appendTo(this.itemsDiv);
        let icon = $('<span class="icon material-icons"/>').appendTo(el);
        let text = $('<span/>').text(itm[1]).appendTo(el);

        function setSelected(selected) {
            self.selection[code].active = selected;
            if (selected) {
                el.addClass('selected-item');
                icon.addClass('md-green').removeClass('md-red');
                icon.text('check_circle_outline');
            } else {
                el.removeClass('selected-item');
                icon.addClass('md-red').removeClass('md-green');
                icon.text('highlight_off');
            }
        }

        this.selection[code] = {
            selected: initSel,
            active: initSel, // active includes temporary selection
            el: el,
            icon: icon,
            text: text,
            select: setSelected,
        };

        setSelected(initSel);

        el.on('click', function(e) {
            if (!self.active) return;
            e.stopPropagation();
            // toggle selection of this item
            let newsel = !self.selection[code].active;
            setSelected(newsel);
        });
    }

    this.divOuter.removeClass(['empty', 'full']);
    if (numSelected == 0) {
        this.divOuter.addClass('empty');
    } else if (numSelected == Object.keys(this.selection).length) {
        this.divOuter.addClass('full');
    }

    this.divBtns = $('<div/>').addClass('buttons mt-1').appendTo(this.divOuter);
    this.btnCancel = $('<input type="button"/>').val('Cancel').appendTo(this.divBtns).on('click', function (e) {
        e.stopPropagation();
        self.close(true);
    });
    this.btnOk = $('<input type="button" />').val('OK').appendTo(this.divBtns).on('click', function (e) {
        e.stopPropagation();
        if (onSelect) { // callback when OK is pressed
            let selectedItems = Object.entries(self.selection).filter(([code, {active}]) => active).map(([code, _]) => code);
            onSelect(selectedItems) && self.close(false);
        }
    });

}

MultipleSelect.prototype.doSelectAll = function (allState) {
    Object.values(this.selection).forEach((selItm) => selItm.select(allState));
}

MultipleSelect.prototype.open = function () {
    this.divOuter.removeClass(['collapsed', 'empty', 'full']);
    this.active = true;
}

MultipleSelect.prototype.close = function (reset) {
    let self = this;
    this.active = false;
    this.divOuter.addClass('collapsed');

    let numSelected = 0;
    Object.entries(self.selection).forEach(([code, {selected, active, select}]) => {
        if (reset) {
            self.selection[code].active = selected; // revert selection
        } else {
            selected = self.selection[code].selected = active; // apply selection
        }
        if (selected) numSelected++;
        select(selected);
    });

    this.divOuter.removeClass(['empty', 'full']);
    if (numSelected == 0) {
        this.divOuter.addClass('empty');
    } else if (numSelected == Object.keys(this.selection).length) {
        this.divOuter.addClass('full');
    }
};

function loadMultipleSelectFilter(baseQuery, noItemsQuery, lookup, containerId, items, selected) {
    let container = $(containerId);
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