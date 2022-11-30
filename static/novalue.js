/**
 * https://www.datatables.net/plug-ins/sorting/novalue
 */

var novalue = '—';

$.extend( $.fn.dataTableExt.oSort, {

    "sethigh-asc": function ( a, b ) {

        let x = a;
        let y = b;

             if (x == novalue && y != novalue) { return  1; }
        else if (x != novalue && y == novalue) { return -1; }
        else if (x == novalue && y == novalue) { return  0; }
        else if (x != novalue && y != novalue) {

            x = parseFloat(a);
            y = parseFloat(b);

            return ( (x < y) ? -1 : ( (x > y) ? 1 : 0 ) );
        }
    },
    "sethigh-desc": function ( a, b ) {

        let x = a;
        let y = b;

             if (x == novalue && y != novalue) { return -1; }
        else if (x != novalue && y == novalue) { return  1; }
        else if (x == novalue && y == novalue) { return  0; }
        else if (x != novalue && y != novalue) {

            x = parseFloat(a);
            y = parseFloat(b);

            return ( (x < y) ? 1 : ( (x > y) ? -1 : 0 ) );
        }
    },

    "setlow-asc": function ( a, b ) {

        let x = a;
        let y = b;

             if (x == novalue && y != novalue) { return -1; }
        else if (x != novalue && y == novalue) { return  1; }
        else if (x == novalue && y == novalue) { return  0; }
        else if (x != novalue && y != novalue) {

            x = parseFloat(a);
            y = parseFloat(b);

            return ( (x < y) ? -1 : ( (x > y) ? 1 : 0 ) );
        }
    },
    "setlow-desc": function ( a, b ) {

        let x = a;
        let y = b;

             if (x == novalue && y != novalue) { return  1; }
        else if (x != novalue && y == novalue) { return -1; }
        else if (x == novalue && y == novalue) { return  0; }
        else if (x != novalue && y != novalue) {

            x = parseFloat(a);
            y = parseFloat(b);

            return ( (x < y) ? 1 : ( (x > y) ? -1 : 0 ) );
        }
    }
});
