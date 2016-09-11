:top
/^[0-9]\+\r$/ b title
/^ACT/ { x; s/ACT.*$//; s/.$//; G; x }
/factions.*friends/ { x; p; x; p; i\

}
d # goes to top

:title
n; /^.$/ n; x; d; b top;
