/** Django multiple select, copyright Felix von Perger (2023) under Creative Commons license */

function MultipleSelect(container, items, initial, onSelect) {
    let self = this;
    this.onSelect = onSelect;
    initial = initial || [];
    this.items = items || [];
    this.selection = {}; // per item code: {selected: true/false, el: JQueryElement}
    this.active = false;

    this.divOuter = $('<ul/>').addClass('multiple-select collapsed').appendTo(container);

    this.divOuter.on('click', function(e) {
        console.log('ul click');
        if (!self.active) {
            self.open();
        }
    });

    this.divSelectBtns = $('<li/>').addClass('buttons mb-1').appendTo(this.divOuter);
    this.btnAll = $('<button type="button" class="btn-sm btn-outline-prmary me-1"/>').text('All').appendTo(this.divSelectBtns).on('click', (e) => {
        e.stopPropagation();
        self.doSelectAll(true);
    });
    this.btnNone = $('<button type="button" class="btn-sm btn-outline-secondary"/>').text('None').appendTo(this.divSelectBtns).on('click', (e) => {
        e.stopPropagation();
        self.doSelectAll(false);
    });

    for (var itm of items) {
        let code = itm[0];
        let initSel = initial.includes(code);
        let el = $('<li/>').addClass('item').appendTo(this.divOuter);
        let icon = $('<span class="icon material-icons"/>').appendTo(el);
        let text = $('<span/>').text(itm[1]).appendTo(el);

        function setSelected(selected) {
            self.selection[code].active = selected;
            if (selected) {
                el.addClass('selected');
                icon.addClass('md-green');
                icon.text('check_circle_outline');
            } else {
                el.removeClass('selected');
                icon.addClass('md-red');
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

    this.divBtns = $('<li/>').addClass('buttons mt-1').appendTo(this.divOuter);
    this.btnCancel = $('<button type="button" class="btn-sm btn-secondary me-1"/>').text('Cancel').appendTo(this.divBtns).on('click', function (e) {
        e.stopPropagation();
        self.close(true);
    });
    this.btnOk = $('<button type="button" class="btn-sm btn-primary"/>').text('OK').appendTo(this.divBtns).on('click', function (e) {
        e.stopPropagation();
        self.close(false);
        if (onSelect) { // callback when OK is pressed
            let selectedItems = Object.entries(self.selection).filter(([code, {active}]) => active).map(([code, _]) => code);
            onSelect(selectedItems);
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

function loadMultipleSelectFilter(baseQuery, noItemsQuery, containerId, items, selected) {
    let container = $(containerId);
    let ms = MultipleSelect(container, items, selected, function (newSelected) {
        // construct query string based on selection
        if (newSelected.length == items.length) {
            window.location = window.location.pathname + baseQuery; // no filter (show all)
        } else if (newSelected.length > 0) {
            let amp = baseQuery === '?' ? '' : '&';
            window.location = window.location.pathname + baseQuery + amp + newSelected.join(',');
        } else {
            window.location = window.location.pathname + noItemsQuery; // filter for only null values
        }
    });
}